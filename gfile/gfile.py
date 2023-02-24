import concurrent.futures
import io
import math
import re
import time
import uuid
from datetime import datetime
from math import ceil
from pathlib import Path
from urllib.parse import unquote

from requests_toolbelt import MultipartEncoder, StreamingIterator
from tqdm import tqdm


def bytes_to_size_str(bytes):
   if bytes == 0:
       return "0B"
   units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(bytes, 1024)))
   p = math.pow(1024, i)
   return f"{bytes/p:.02f} {units[i]}"


def size_str_to_bytes(size_str):
    if isinstance(size_str, int):
        return size_str
    m = re.search(r'^(?P<num>\d+) ?((?P<unit>[KMGTPEZY]?)(iB|B)?)$', size_str, re.IGNORECASE)
    assert m
    units = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    unit = (m['unit'] or 'B').upper()
    return int(math.pow(1024, units.index(unit)) * int(m['num']))


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
        self.chunk_size = size_str_to_bytes(chunk_size)
        self.chunk_copy_size = size_str_to_bytes(chunk_copy_size)
        self.thread_num=thread_num
        self.progress = progress
        self.data = None
        self.pbar = None
        self.session = requests_retry_session()
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

        bar = self.pbar[chunk_no % self.thread_num] if self.pbar else None
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
            # convert the form-data into a binary string, this way we can control/throttle its read() behavior
            form_data_binary = form_data.to_string()
            del form_data

        size = len(form_data_binary)
        if bar:
            bar.desc = f'chunk {chunk_no + 1}/{chunks}'
            bar.reset(total=size)
            # bar.refresh()

        def gen():
            offset = 0
            while True:
                if offset < size:
                    update_tick = 1024 * 128
                    yield form_data_binary[offset:offset+update_tick]
                    if bar:
                        bar.update(min(update_tick, size - offset))
                        bar.refresh()
                    offset += update_tick
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
        assert Path(self.uri).exists()
        size = Path(self.uri).stat().st_size
        chunks = ceil(size / self.chunk_size)
        print(f'Filesize {bytes_to_size_str(size)}, chunk size: {bytes_to_size_str(self.chunk_size)}, total chunks: {chunks}')

        if self.progress:
            self.pbar = []
            for i in range(self.thread_num):
                self.pbar.append(tqdm(total=size, unit="B", unit_scale=True, leave=False, unit_divisor=1024, ncols=100, position=i))
        self.session = requests_retry_session()
        self.server = re.search(r'var server = "(.+?)"', self.session.get('https://gigafile.nu/').text)[1]

        # upload the first chunk to set cookies properly.
        self.upload_chunk(0, chunks)

        # upload second to second last chunk(s)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_num) as ex:
            futures = {ex.submit(self.upload_chunk, i, chunks): i for i in range(1, chunks)}
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

        # upload last chunk if not already
        # if chunks > 1:
        #     # print('\nupload the last chunk in single thread')
        #     self.upload_chunk(chunks - 1, chunks)

        if self.pbar:
            for bar in self.pbar:
                bar.close()
        print('')
        if 'url' not in self.data:
            print('Something went wrong. Upload failed.', self.data)
        return self # for chain


    def get_download_page(self):
        if not self.data or not 'url' in self.data:
            return
        f = Path(self.uri)
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, filename: {f.name}, size: {bytes_to_size_str(f.stat().st_size)}")
        print(self.data['url'])
        return self.data['url']


    def download(self, filename=None):
        m = re.search(r'^https?:\/\/\d+?\.gigafile\.nu\/([a-z0-9-]+)$', self.uri)
        if not m:
            print('Invalid URL.')
            return
        self.session.get(self.uri) # setup cookie
        file_id = m[1]
        download_url = self.uri.replace(file_id, 'download.php?file=' + file_id)
        with self.session.get(download_url, stream=True) as r:
            r.raise_for_status()
            filesize = int(r.headers['Content-Length'])
            if not filename:
                filename = 'gigafile_noname.bin' # temp name
                content_disp = r.headers['Content-Disposition']
                if "UTF-8''" in content_disp:
                    filename = unquote(content_disp.split("UTF-8''")[-1])
                else:
                    filename = re.search(r'filename="(.+?)";', content_disp)[1].encode('iso8859-1','ignore').decode('utf-8', 'ignore')
                filename = re.sub(r'[\\/:*?"<>|]', '_', filename) # only sanitize remote filename. User provided ones are on users' own.
            if self.progress:
                self.pbar = tqdm(total=filesize, unit='B', unit_scale=True, unit_divisor=1024, desc=filename)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=self.chunk_copy_size):
                    f.write(chunk)
                    if self.pbar: self.pbar.update(len(chunk))
        if self.pbar: self.pbar.close()

        filesize_downloaded = Path(filename).stat().st_size
        print(f'Filesize check: expected: {filesize}; actual: {filesize_downloaded}. {"Succeeded." if filesize==filesize_downloaded else "Failed!"}')
        return filename
