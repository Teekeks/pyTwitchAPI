#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
from .twitch import Twitch
from .types import *
import asyncio
import websockets
import threading
from .helper import TWITCH_PUB_SUB_URL
import json
import random
import datetime
import logging


class PubSub:

    ping_frequency: int = 120
    """:var int ping_frequency: with which frequency in seconds a ping command is send.
                                You probably dont want to change this.
                                Default: 120"""
    ping_jitter: int = 4
    """:var int ping_jitter: time in seconds added or subtracted from ping_frequency.
                             You probably dont want to change this.
                             Default: 4"""

    __twitch: Twitch = None
    __connection = None
    __socket_thread: threading.Thread = None
    __running: bool = False
    __socket_loop = None
    __topics: dict = {}

    def __init__(self, twitch: Twitch):
        self.__twitch = twitch

    async def __connect(self):
        self.__connection = await websockets.connect(TWITCH_PUB_SUB_URL)
        if self.__connection.open:
            listen_msg = {
                'type': 'LISTEN',
                'data': {
                    'topics': list(self.__topics.keys()),
                    'auth_token': self.__twitch.get_user_auth_token()
                }
            }
            await self.__send_message(listen_msg)

    async def __send_message(self, msg_data):
        await self.__connection.send(json.dumps(msg_data))

    def __run_socket(self):
        self.__socket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__socket_loop)

        # startup
        self.__socket_loop.run_until_complete(self.__connect())

        tasks = [
            asyncio.ensure_future(self.__task_heartbeat(), loop=self.__socket_loop),
            asyncio.ensure_future(self.__task_receive(), loop=self.__socket_loop)
        ]
        try:
            self.__socket_loop.run_forever()
        except asyncio.CancelledError:
            pass

    async def __task_heartbeat(self):
        while True:
            next_heartbeat = datetime.datetime.utcnow() + \
                             datetime.timedelta(seconds=random.randrange(self.ping_frequency - self.ping_jitter,
                                                                         self.ping_frequency + self.ping_jitter,
                                                                         1))
            while datetime.datetime.utcnow() < next_heartbeat:
                await asyncio.sleep(1)
            logging.debug('send ping...')
            await self.__send_message({'type': 'PING'})

    async def __task_receive(self):
        async for message in self.__connection:
            data = json.loads(message)
            from pprint import pprint
            pprint(data)

    def start(self):
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()

    def listen_whispers(self,
                        user_id: str):
        self.__topics[f'whispers.{user_id}'] = {}

