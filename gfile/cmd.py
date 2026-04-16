
import argparse
from enum import Enum

if __name__ == '__main__' and __package__ is None:
    from gfile import GFile
    from __init__ import __version__
else:
    from .gfile import GFile
    from . import __version__

class Action(Enum):
    download = 'download'
    upload = 'upload'
    def __str__(self):
        return self.value

def main():
    parser = argparse.ArgumentParser(prog='Gfile')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}', help='show version and exit')
    parser.add_argument('action', type=Action, choices=list(Action), help='upload or download')
    parser.add_argument('file_or_url', help='filename to upload or url to download')
    parser.add_argument('-p', '--hide-progress', dest='progress', action='store_false', default=True, help='hide progress bar')
    parser.add_argument('-o', '--output', type=str, default=None, help='output filename for download (default: use original name)')
    parser.add_argument('--aria2', nargs='?', const="-x10 -s10", default=None, help='download with aria2. You can also specify optional arguments (default: "-x10 -s10", make sure to quote). `-o` is already automatically included.')
    parser.add_argument('-n', '--thread-num', dest='thread_num', default=8, type=int, help='number of threads used for upload [default: 8]')
    parser.add_argument('-s', '--chunk-size', dest='chunk_size', default="100MB", help='chunk size per upload in bytes; note: chunk_size*thread will be loaded into memory [default: 100MB]')
    parser.add_argument('-m', '--copy-size', dest='chunk_copy_size', default="1MB", help='specifies size to copy the main file into pieces [default: 1MB]')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='specifies timeout time (in seconds) [default: 10]')
    parser.add_argument('-k', '--key', '--password', dest='key', default=None, help='specifies the key/password for the file')
    parser.add_argument('--mute', action='store_true', help='mute initial message and warnings (only the final result and errors will be shown)')
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument('--verify', dest='verify', action='store_true', default=True, help='enable verification (default)')
    verify_group.add_argument('--no-verify', dest='verify', action='store_false', help='disable verification')
    parser.add_argument('--resume', dest='resume', action='store_true', default=True, help='resume incomplete downloads (default)')

    args = parser.parse_args()

    gf = GFile(**args.__dict__)
    if args.action == Action.download:
        gf.download(args.output)
    else:
        gf.upload().get_download_page()

if __name__ == "__main__":
    main()
