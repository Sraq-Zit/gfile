
import argparse
from enum import Enum
from datetime import datetime
from pathlib import Path
import math

if __name__ == "__main__": from gfile import GFile
else:                      from .gfile import GFile

class Action(Enum):
    download = 'download'
    upload = 'upload'
    def __str__(self):
        return self.value


def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   return f"{size_bytes/p:.02f} {units[i]}"

def main():
    parser = argparse.ArgumentParser(prog='Gfile')
    parser.add_argument('action', type=Action, choices=list(Action), help='upload or download')
    parser.add_argument('uri', help='filename to upload or url to download')
    parser.add_argument('-p', '--hide-progress', dest='progress', action='store_false', default=True, help='hide progress bar')
    # parser.add_argument('-o', '--output', dest='output file', type=str, default=None, help='hide progress bar') #not implemented
    parser.add_argument('-n', '--thread-num', dest='thread_num', default=8, type=int, help='number of threads used for upload (can incease speed)')
    parser.add_argument('-s', '--chunk-size', dest='chunk_size', type=int, help='gigafile allowed chunk size per upload', default=1024*1024*100)
    parser.add_argument('-m', '--copy-size', dest='chunk_copy_size', type=int, help='specifies size to copy the main file into pieces (the size loaded in RAM)', default=1024*1024)

    args = parser.parse_args()

    gf = GFile(**args.__dict__)
    if args.action == Action.download:
        gf.download(args.chunk_copy_size, args.progress)

    else:
        url = gf.upload().get_download_page()
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, filename: {gf.uri}, size: {convert_size(Path(gf.uri).stat().st_size)}")
        print(url)

if __name__ == "__main__":
    main()
