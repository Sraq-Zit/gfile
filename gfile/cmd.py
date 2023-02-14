
import argparse
from enum import Enum

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
    parser.add_argument('-o', '--output', type=str, default=None, help='output filename for download')
    parser.add_argument('-n', '--thread-num', dest='thread_num', default=8, type=int, help='number of threads used for upload [default: 8]')
    parser.add_argument('-s', '--chunk-size', dest='chunk_size', default="100MB", help='chunk size per upload in bytes; note: chunk_size*thread will be loaded into memory [default: 100MB]')
    parser.add_argument('-m', '--copy-size', dest='chunk_copy_size', default="1MB", help='specifies size to copy the main file into pieces [default: 1MB]')

    args = parser.parse_args()

    gf = GFile(**args.__dict__)
    if args.action == Action.download:
        gf.download(args.output)
    else:
        gf.upload()

if __name__ == "__main__":
    main()
