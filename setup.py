#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
from setuptools import setup, find_packages

version = ""

with open('twitchAPI/__init__.py') as f:
    for line in f.readlines():
        if line.startswith('__version__'):
            version = line.split('= \'')[-1][:-2].strip()

setup(
    packages=find_packages(),
    version=version,
    install_requires=[
        'aiohttp',
        'python-dateutil',
        'typing_extensions'
    ]
)
