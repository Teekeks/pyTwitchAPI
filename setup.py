#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from setuptools import setup, find_packages
setup(
    packages=find_packages(),
    package_data={
        "twitchAPI": ["*.html"]
    },
    install_requires=['requests', 'python-dateutil', 'aiohttp']
)
