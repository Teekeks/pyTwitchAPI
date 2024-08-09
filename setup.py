#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
from setuptools import setup, find_packages

version = ''

with open('twitchAPI/__init__.py') as f:
    for line in f.readlines():
        if line.startswith('__version__'):
            version = line.split('= \'')[-1][:-2].strip()

if version.endswith(('a', 'b', 'rc')):
    try:
        import subprocess
        p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            version += out.decode('utf-8').strip()
        p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            version += '+g' + out.decode('utf-8').strip()
    except:
        pass

setup(
    packages=find_packages(),
    version=version,
    keywords=['twitch', 'twitch.tv', 'chat', 'bot', 'event sub', 'EventSub', 'pub sub', 'PubSub', 'helix', 'api'],
    install_requires=[
        'aiohttp>=3.9.3',
        'python-dateutil>=2.8.2',
        'typing_extensions',
        'enum-tools'
    ],
    package_data={'twitchAPI': ['py.typed']}
)
