import concurrent.futures
import re
import uuid
from math import ceil
from pathlib import Path
import io
from requests_toolbelt import MultipartEncoder, StreamingIterator
from tqdm import tqdm
import time
from urllib.parse import unquote

def requests_retry_session(
    retries=5,
    backoff_factor=0.2,
    status_forcelist=None, # (500, 502, 504)
    session=None,
):
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = session or requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def split_file(input_file, out, target_size=None, start=0, chunk_copy_size=1024*1024):
    input_file = Path(input_file)
    size = 0

    input_size = input_file.stat().st_size
    if target_size is None:
        output_size = input_size - start
    else:
        output_size = min( target_size, input_size - start)

    with open(input_file, 'rb') as f:
        f.seek(start)
        while True:
            # print(f'{size / output_size * 100:.2f}%', end='\r')
            if size == output_size: break
            if size > output_size:
                raise Exception(f'Size ({size}) is larger than {target_size} bytes!')
            current_chunk_size = min(chunk_copy_size, output_size - size)
            chunk = f.read(current_chunk_size)
            if not chunk: break
            size += len(chunk)
            out.write(chunk)

class GFile:

    def __init__(self, uri, progress=False, thread_num=4, chunk_size=1024*1024*10, chunk_copy_size=1024*1024, **kwargs) -> None:
        self.uri = uri
        self.chunk_size = chunk_size
        self.chunk_copy_size = chunk_copy_size
        self.thread_num=thread_num
        self.progress = progress
        self.data = None
        self.pbar: tqdm = None
        self.session = requests_retry_session()
        self.index = 0
        self.cookies = None
        self.current_chunk = 0


    def upload_chunk(self, chunk_no, chunks):
        # import tracemalloc

        # tracemalloc.start()
        # prev = tracemalloc.get_traced_memory()[0]

        # def memo(text=''):
        #     nonlocal prev

        #     current = tracemalloc.get_traced_memory()[0]
        #     print(f'Memory change at {text}', current - prev)
        #     prev = current

        # memo('Before load')
        with io.BytesIO() as f:
            split_file(self.uri, f, self.chunk_size, start=chunk_no * self.chunk_size, chunk_copy_size=self.chunk_copy_size)
            chunk_size = f.tell()
            f.seek(0)
            fields = {
                "id": self.token,
                "name": Path(self.uri).name,
                "chunk": str(chunk_no),
                "chunks": str(chunks),
                "lifetime": "100",
                "file": ("blob", f, "application/octet-stream"),
            }
            form_data = MultipartEncoder(fields)
            headers = {
                "content-type": form_data.content_type,
            }
            # convert the form-data into a binary string, this way we can control throttle its read() behavior
            form_data_binary = form_data.to_string()
            del form_data

        size = len(form_data_binary)

        def gen():
            offset = 0
            while True:
                if offset < size:
                    yield form_data_binary[offset:offset+1024]
                    offset += 1024
                else:
                    if chunk_no != self.current_chunk:
                        time.sleep(0.01)
                    else:
                        time.sleep(0.1)
                        break

        streamer = StreamingIterator(size, gen())

        # print("Session gfsid:", self.session.cookies['gfsid'])
        # print(f'Updating chunk {chunk_no + 1} out of {chunks} chunks')
        resp = self.session.post(f"https://{self.server}/upload_chunk.php", data=streamer, headers=headers)
        self.current_chunk += 1
        if self.pbar:
            self.pbar.desc = f'Finished {chunk_no + 1}/{chunks} chunks'
            self.pbar.update(chunk_size)
        # print("Session gfsid after uploading:", self.session.cookies['gfsid'])
        # print('resp', resp.cookies.__dict__)
        resp_data = resp.json()
        # print(resp_data)
        if 'url' in resp_data:
            self.data = resp_data
        if 'status' not in resp_data or resp_data['status']:
            print(resp_data)
            self.failed = True

    def upload(self):
        self.token = uuid.uuid1().hex
        self.pbar = None
        self.failed = False
        self.index = 0
        assert Path(self.uri).exists()
        size = Path(self.uri).stat().st_size
        chunks = ceil(size / self.chunk_size)
        print(f'Total chunks: {chunks}')

        if self.progress:
            self.pbar = tqdm(total=size, unit="B", unit_scale=True, leave=False, unit_divisor=1024, ncols=100)

        self.session = requests_retry_session()
        self.server = re.search(r'var server = "(.+?)"', self.session.get('https://gigafile.nu/').text)[1]

        # upload the first chunk
        self.upload_chunk(0, chunks)

        # for i in range(1, chunks-1):
        #     self.upload_chunk(i, chunks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_num) as ex:
            futures = {ex.submit(self.upload_chunk, i, chunks): i for i in range(1, chunks - 1)}
            try:
                for future in concurrent.futures.as_completed(futures):
                    if self.failed:
                        print('Failed!')
                        for future in futures:
                            future.cancel()
                        return
            except KeyboardInterrupt:
                print('\nUser cancelled the operation.')
                for future in futures:
                    future.cancel()
                return

        if chunks > 1:
            print('\nupload the last chunk in single thread')
            self.upload_chunk(chunks - 1, chunks)

        if self.pbar:
            self.pbar.close()
        if 'url' not in self.data:
            print('something went wrong', self.data)
        # except KeyboardInterrupt:
        #     self.pbar.close()
        #     self.failed = True
        #     print('Aborted! cleaning...')
        return self

    def get_download_page(self): return self.data and self.data['url']
    def get_file_id(self): return self.data and self.data['filename']

    def get_download(self):
        _data: dict[str, str] = self.data
        if not Path(self.uri).exists():
            data = re.search(r'^https?:\/\/\d+?\.gigafile\.nu\/([a-z0-9-]+)$', self.uri)
            if data:
                _data = {'url': self.uri, 'filename': data[1]}
            else:
                raise ValueError('URL invalid')

        if not _data:
            return ValueError('You specified no file to upload nor to download')

        sess = requests_retry_session()
        sess.get(_data['url'])
        return (_data['url'].replace(_data['filename'], 'download.php?file='+_data['filename']), sess.cookies)

    def download(self, copy_size=1024*1024, progress=True, filename=None):
        url, cookies = self.get_download()
        if not filename:
            headers = requests_retry_session().head(url, cookies=cookies).headers
            filesize = int(headers['Content-Length'])
            if "UTF-8''" in headers['Content-Disposition']:
                filename = unquote(headers['Content-Disposition'].split("UTF-8''")[-1])
            else:
                filename = re.search(r'filename="(.+?)";', headers['Content-Disposition'])[1].encode('iso8859-1','ignore').decode('utf-8', 'ignore')
            filename = re.sub(r'\\|\/|:|\*|\?|"|<|>|\|', '_', filename)
        if progress:
            pbar = tqdm(total=filesize, unit='B', unit_scale=True, unit_divisor=1024, desc=filename, ncols=100)

        with open(filename, 'wb') as f:
            with requests_retry_session().get(url, cookies=cookies, stream=True) as req:
                req.raise_for_status()
                for chunk in req.iter_content(chunk_size=copy_size):
                    f.write(chunk)
                    if pbar: pbar.update(len(chunk))
        return filename
