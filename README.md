A python module to download and upload from [gigafile](https://gigafile.nu/).

# Install
    $ python setup.py install --user
or

    $ pip install git+https://github.com/Sraq-Zit/gfile.git -U

# Usage
## Module
### Import
```py
from gfile import GFile
```
### Download
```py
filename = GFile('https://XX.gigafile.nu/YYY').download()
```

### Upload
```py
url = GFile('path/to/file', progress=True).upload().get_download_page()
```

## CLI
```bash
$ gfile upload path/to/file

$ gfile download https://66.gigafile.nu/0320-b36ec21d4a56b143537e12df7388a5367

$ gfile -h
usage: Gfile [-h] [-p] [-o OUTPUT] [-n THREAD_NUM] [-s CHUNK_SIZE] [-m CHUNK_COPY_SIZE] {download,upload} uri

positional arguments:
  {download,upload}     upload or download
  uri                   filename to upload or url to download

options:
  -h, --help            show this help message and exit
  -p, --hide-progress   hide progress bar
  -o OUTPUT, --output OUTPUT
                        output filename for download
  -n THREAD_NUM, --thread-num THREAD_NUM
                        number of threads used for upload [default: 8]
  -s CHUNK_SIZE, --chunk-size CHUNK_SIZE
                        chunk size per upload in bytes; note: chunk_size*thread will be loaded into memory [default: 100MB]
  -m CHUNK_COPY_SIZE, --copy-size CHUNK_COPY_SIZE
                        specifies size to copy the main file into pieces [default: 1MB]
```