#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from setuptools import setup, find_packages
setup(
    packages=find_packages(),
    name="twitchAPI",
    version="2.5.0",
    url="https://github.com/Teekeks/pyTwitchAPI",
    author="Lena \"Teekeks\" During",
    author_email="info@teawork.de",
    description="A Python 3.7+ implementation of the Twitch Helix API, its Webhook, PubSub and EventSub",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
    ],
    package_data={
        "twitchAPI": ["*.html"],
        "twitchAPI.res": ["*.html"]
    },
    install_requires=['requests', 'python-dateutil', 'aiohttp', 'websockets', 'typing_extensions']
)
