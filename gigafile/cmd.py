
import argparse
from enum import Enum
import re

from tqdm import tqdm
import requests as r
if __name__ == "__main__": from gigafile import GigaFile
else:                      from .gigafile import GigaFile

class Action(Enum):
    download = 'download'
    upload = 'upload'
    def __str__(self):
        return self.value
    


def main():
    parser = argparse.ArgumentParser(prog='Gigafile')
    parser.add_argument('action', type=Action, choices=list(Action), help='upload or download')
    parser.add_argument('uri', help='filename to upload or url to download')
    parser.add_argument('-p', '--hide-progress', dest='progress', action='store_false', default=True, help='hide progress bar')
    parser.add_argument('-n', '--thread-num', dest='thread_num', default=int(4), type=int, help='number of threads used for upload (can incease speed)')
    parser.add_argument('-s', '--chunk-size', dest='chunk_size', type=int, help='gigafile allowed chunk size per upload', default=1024*1024*100)
    parser.add_argument('-m', '--copy-size', dest='chunk_copy_size', type=int, help='specifies size to copy the main file into pieces (the size loaded in RAM)', default=1024*1024)

    args = parser.parse_args()

    gf = GigaFile(**args.__dict__)
    if args.action == Action.download:
        pbar = None
        url, cookies = gf.direct_download()
        headers = r.head(url, cookies=cookies).headers
        filesize = int(headers['Content-Length'])
        filename = re.search(r'filename="(.+?)";', headers['Content-Disposition'])[1]
        filename = re.sub(r'\\|\/|:|\*|\?|"|<|>|\|', '_', filename)
        if args.progress:
            pbar = tqdm(total=filesize, unit='B', unit_scale=True, desc=filename)
            
        with open(filename, 'wb') as f:
            with r.get(url, cookies=cookies, stream=True) as req:
                req.raise_for_status()
                for chunk in req.iter_content(chunk_size=args.chunk_copy_size):
                    f.write(chunk)
                    if pbar: pbar.update(len(chunk))

    else:
        print(gf.upload().get_download_page())
        
if __name__ == "__main__":
    main()
