from setuptools import setup

setup(
    name='gigafile',
    version='1.0',
    description='A python module to download and upload from gigafile.nu',
    author='Sraqzit',
    author_email='kingofmestry@gmail.com',
    install_requires=['requests==2.25.1', 'requests_toolbelt==0.9.1', 'tqdm==4.61.2'],
    requires=[],
    packages=['gigafile'],
    entry_points={
        'console_scripts': [
           'gfile = gigafile.cmd:main',
        ],
    },
)
