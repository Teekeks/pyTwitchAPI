#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
from .twitch import Twitch
from .types import *
import asyncio
import websockets
import threading
from .helper import TWITCH_PUB_SUB_URL
import json


class PubSub:

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
            asyncio.ensure_future(self.__task_heartbeat(), loop=self.__socket_loop)
        ]
        try:
            self.__socket_loop.run_forever()
        except asyncio.CancelledError:
            pass

    async def __task_heartbeat(self):
        while True:
            pass

    def start(self):
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
