A python module to download and upload from [gigafile](https://gigafile.nu/).

# Install

    $ python setup.py install --user

# Usage

    $ gfile upload path/to/file

    $ gfile download https://66.gigafile.nu/0320-b36ec21d4a56b143537e12df7388a5367

    $ gfile -h
    usage: Gfile [-h] [-p] [-n THREAD_NUM] [-s CHUNK_SIZE] [-m CHUNK_COPY_SIZE] {download,upload} uri

    positional arguments:
    {download,upload}     Upload or download
    uri                   Filename to upload or url to download

    optional arguments:
    -h, --help            show this help message and exit
    -p, --hide-progress   Hide progress bar
    -n THREAD_NUM, --thread-num THREAD_NUM
                            Number of threads used for upload (can incease speed)
    -s CHUNK_SIZE, --chunk-size CHUNK_SIZE
                     allowed chunk size per upload
    -m CHUNK_COPY_SIZE, --copy-size CHUNK_COPY_SIZE
                            Specifies size to copy the main file into pieces (the size loaded in RAM)

