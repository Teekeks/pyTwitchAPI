#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from distutils.core import setup
setup(
  name = 'twitchAPI',
  packages = ['twitchAPI'],
  version = '0.1',
  license='MIT',
  description = 'A Python 3.7 implementation of the Twitch API and its Webhook',
  author = 'Lena "Teekeks" During',
  author_email = 'info@teawork.de',
  url = 'https://github.com/Teekeks/pyTwitchAPI',
  download_url = 'https://github.com/Teekeks/pyTwitchAPI/archive/v0.1.tar.gz',
  keywords = ['twitch', 'webhook', 'helix'],
  install_requires=[
          'aiohttp',
          'requests',
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8'
  ],
)