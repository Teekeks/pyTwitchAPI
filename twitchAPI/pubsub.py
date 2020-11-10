#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Pubsub client
-------------"""

from .twitch import Twitch
from .types import *
from .helper import get_uuid, make_enum
import asyncio
import websockets
import threading
from .helper import TWITCH_PUB_SUB_URL
import json
import random
import datetime
import logging
from typing import Callable, List
from uuid import UUID
import time


class PubSub:
    """The Pubsub client

    :var int ping_frequency: with which frequency in seconds a ping command is send.
                                You probably dont want to change this.
                                This should never be shorter than 12 + ping_jitter seconds to avoid problems
                                with the pong timeout.
                                |default| :code:`120`
    :var int ping_jitter: time in seconds added or subtracted from ping_frequency.
                             You probably dont want to change this.
                             |default| :code:`4`
    :var int listen_confirm_timeout: maximum time in seconds waited for a listen confirm.
                                        |default| :code:`30`
    """

    ping_frequency: int = 120
    ping_jitter: int = 4
    listen_confirm_timeout: int = 30

    __twitch: Twitch = None
    __connection = None
    __socket_thread: threading.Thread = None
    __running: bool = False
    __socket_loop = None
    __topics: dict = {}
    __startup_complete: bool = False

    __tasks = None

    __waiting_for_pong: bool = False
    __logger: logging.Logger = None
    __nonce_waiting_confirm: dict = {}

    def __init__(self, twitch: Twitch):
        self.__twitch = twitch
        self.__logger = logging.getLogger('twitchAPI.pubsub')

    async def __connect(self, is_startup=False):
        if self.__connection is not None and self.__connection.open:
            await self.__connection.close()
        self.__connection = await websockets.connect(TWITCH_PUB_SUB_URL, loop=self.__socket_loop)
        if self.__connection.open and not is_startup:
            uuid = str(get_uuid())
            await self.__send_listen(uuid, list(self.__topics.keys()))

    async def __send_listen(self, nonce: str, topics: List[str], subscribe: bool = True):
        listen_msg = {
            'type': 'LISTEN' if subscribe else 'UNLISTEN',
            'nonce': nonce,
            'data': {
                'topics': topics,
                'auth_token': self.__twitch.get_user_auth_token()
            }
        }
        self.__nonce_waiting_confirm[nonce] = {'received': False,
                                               'error': PubSubResponseError.NONE}
        timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.listen_confirm_timeout)
        confirmed = False
        self.__logger.debug(f'sending {"" if subscribe else "un"}listen for topics {str(topics)} with nonce {nonce}')
        await self.__send_message(listen_msg)
        # wait for confirm
        while not confirmed and datetime.datetime.utcnow() < timeout:
            await asyncio.sleep(0.01)
            confirmed = self.__nonce_waiting_confirm[nonce]['received']
        if not confirmed:
            raise PubSubListenTimeoutException()
        else:
            error = self.__nonce_waiting_confirm[nonce]['error']
            if error is not PubSubResponseError.NONE:
                if error is PubSubResponseError.BAD_AUTH:
                    raise TwitchAuthorizationException()
                if error is PubSubResponseError.SERVER:
                    raise TwitchBackendException()
                raise TwitchAPIException(error)

    async def __send_message(self, msg_data):
        await self.__connection.send(json.dumps(msg_data))

    def __run_socket(self):
        self.__socket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__socket_loop)

        # startup
        self.__socket_loop.run_until_complete(self.__connect(is_startup=True))

        self.__tasks = [
            asyncio.ensure_future(self.__task_heartbeat(), loop=self.__socket_loop),
            asyncio.ensure_future(self.__task_receive(), loop=self.__socket_loop),
            asyncio.ensure_future(self.__task_initial_listen(), loop=self.__socket_loop)
        ]

        try:
            self.__socket_loop.run_forever()
        except asyncio.CancelledError:
            pass
        if self.__connection.open:
            self.__socket_loop.run_until_complete(self.__connection.close())

    async def __task_initial_listen(self):
        self.__startup_complete = True
        if len(list(self.__topics.keys())) > 0:
            uuid = str(get_uuid())
            await self.__send_listen(uuid, list(self.__topics.keys()))

    async def __task_heartbeat(self):
        while True:
            next_heartbeat = datetime.datetime.utcnow() + \
                             datetime.timedelta(seconds=random.randrange(self.ping_frequency - self.ping_jitter,
                                                                         self.ping_frequency + self.ping_jitter,
                                                                         1))

            while datetime.datetime.utcnow() < next_heartbeat:
                await asyncio.sleep(1)
            self.__logger.debug('send ping...')
            pong_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
            self.__waiting_for_pong = True
            await self.__send_message({'type': 'PING'})
            while self.__waiting_for_pong:
                if datetime.datetime.utcnow() > pong_timeout:
                    self.__logger.info('did not receive pong in time, reconnecting...')
                    await self.__connect()
                    self.__waiting_for_pong = False
                await asyncio.sleep(1)

    async def __handle_pong(self, data):
        self.__waiting_for_pong = False
        self.__logger.debug('received pong')

    async def __handle_reconnect(self, data):
        self.__logger.info('received reconnect command, reconnecting now...')
        await self.__connect()

    async def __handle_response(self, data):
        error = make_enum(data.get('error'),
                          PubSubResponseError,
                          PubSubResponseError.UNKNOWN)
        self.__logger.debug(f'got response for nonce {data.get("nonce")}: {str(error)}')
        self.__nonce_waiting_confirm[data.get('nonce')]['error'] = error
        self.__nonce_waiting_confirm[data.get('nonce')]['received'] = True

    async def __handle_message(self, data):
        topic_data = self.__topics.get(data.get('data', {}).get('topic', ''), None)
        msg_data = json.loads(data.get('data', {}).get('message', '{}'))
        if topic_data is not None:
            for uuid, sub in topic_data.get('subs', {}).items():
                sub(uuid, msg_data)

    async def __handle_unknown(self, data):
        self.__logger.warning('got message of unknown type: ' + str(data))

    async def __task_receive(self):
        async for message in self.__connection:
            data = json.loads(message)
            switcher = {
                'pong': self.__handle_pong,
                'reconnect': self.__handle_reconnect,
                'response': self.__handle_response,
                'message': self.__handle_message
            }
            handler = switcher.get(data.get('type', '').lower(),
                                   self.__handle_unknown)
            await handler(data)

    def __ask_exit(self):
        for task in asyncio.Task.all_tasks(loop=self.__socket_loop):
            task.cancel()

    def start(self):
        self.__startup_complete = False
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
        while not self.__startup_complete:
            time.sleep(0.01)

    def stop(self):
        self.__startup_complete = False
        self.__running = False
        for task in self.__tasks:
            task.cancel()
        self.__socket_loop.call_soon_threadsafe(self.__socket_loop.stop)
        self.__socket_thread.join()

    def __generic_listen(self, key, callback_func) -> UUID:
        uuid = get_uuid()
        if key not in self.__topics.keys():
            self.__topics[key] = {'subs': {}}
        self.__topics[key]['subs'][uuid] = callback_func
        if self.__startup_complete:
            asyncio.get_event_loop().run_until_complete(self.__send_listen(str(uuid), [key]))
        return uuid

    def unlisten(self, uuid: UUID):
        clear_topics = []
        for topic, topic_data in self.__topics.items():
            if uuid in topic_data['subs'].keys():
                topic_data['subs'].pop(uuid)
                if len(topic_data['subs'].keys()) == 0:
                    clear_topics.append(topic)
        if self.__startup_complete and len(clear_topics) > 0:
            asyncio.get_event_loop().run_until_complete(self.__send_listen(str(uuid), clear_topics, subscribe=False))
        if len(clear_topics) > 0:
            for topic in clear_topics:
                self.__topics.pop(topic)

    def listen_whispers(self,
                        user_id: str,
                        callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'whispers.{user_id}', callback_func)

    def listen_bits_v1(self,
                       channel_id: str,
                       callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'channel-bits-events-v1.{channel_id}', callback_func)

    def listen_bits(self,
                    channel_id: str,
                    callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'channel-bits-events-v2.{channel_id}', callback_func)

    def listen_bits_badge_notification(self,
                                       channel_id: str,
                                       callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'channel-bits-badge-unlocks.{channel_id}', callback_func)

    def listen_channel_points(self,
                              channel_id: str,
                              callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'channel-points-channel-v1.{channel_id}', callback_func)

    def listen_channel_subscriptions(self,
                                     channel_id: str,
                                     callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'channel-subscribe-events-v1.{channel_id}', callback_func)

    def listen_chat_moderator_actions(self,
                                      user_id: str,
                                      channel_id: str,
                                      callback_func: Callable[[UUID, dict], None]) -> UUID:
        return self.__generic_listen(f'chat_moderator_actions.{user_id}.{channel_id}', callback_func)
