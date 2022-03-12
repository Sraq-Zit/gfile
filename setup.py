from setuptools import setup

setup(
    name='gigafile',
    version='1.0',
    description='A python module to download and upload from gigafile.nu',
    author='Sraqzit',
    author_email='kingofmestry@gmail.com',
    packages=['gigafile'],
    entry_points={
        'console_scripts': [
           'gfile = gigafile.cmd:main',
        ],
    },
)
