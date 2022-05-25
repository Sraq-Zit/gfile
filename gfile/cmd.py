
import argparse
from enum import Enum
import re

from tqdm import tqdm
if __name__ == "__main__": from gfile import GFile
else:                      from .gfile import GFile

class Action(Enum):
    download = 'download'
    upload = 'upload'
    def __str__(self):
        return self.value
    


def main():
    parser = argparse.ArgumentParser(prog='Gfile')
    parser.add_argument('action', type=Action, choices=list(Action), help='upload or download')
    parser.add_argument('uri', help='filename to upload or url to download')
    parser.add_argument('-p', '--hide-progress', dest='progress', action='store_false', default=True, help='hide progress bar')
    parser.add_argument('-n', '--thread-num', dest='thread_num', default=int(4), type=int, help='number of threads used for upload (can incease speed)')
    parser.add_argument('-s', '--chunk-size', dest='chunk_size', type=int, help='gigafile allowed chunk size per upload', default=1024*1024*100)
    parser.add_argument('-m', '--copy-size', dest='chunk_copy_size', type=int, help='specifies size to copy the main file into pieces (the size loaded in RAM)', default=1024*1024)

    args = parser.parse_args()

    gf = GFile(**args.__dict__)
    if args.action == Action.download:
        gf.download(args.chunk_copy_size, args.progress)
        
    else:
        print(gf.upload().get_download_page())
        
if __name__ == "__main__":
    main()
