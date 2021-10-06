#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
PubSub client
-------------

This is a full implementation of the PubSub API of twitch.
PubSub enables you to subscribe to a topic, for updates (e.g., when a user cheers in a channel).

Read more about it on `the Twitch API Documentation <https://dev.twitch.tv/docs/pubsub>`__.

.. note:: You **always** need User Authentication while using this!

*******************
Short code example:
*******************

.. code-block:: python

    from twitchAPI.pubsub import PubSub
    from twitchAPI.twitch import Twitch
    from twitchAPI.types import AuthScope
    from pprint import pprint
    from uuid import UUID

    def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)

    # setting up Authentication and getting your user id
    twitch = Twitch('my_app_id', 'my_app_secret')
    twitch.authenticate_app([])
    # you can get your user auth token and user auth refresh token following the example in twitchAPI.oauth
    twitch.set_user_authentication('my_user_auth_token', [AuthScope.WHISPERS_READ], 'my_user_auth_refresh_token')
    user_id = twitch.get_users(logins=['my_username'])['data'][0]['id']

    # starting up PubSub
    pubsub = PubSub(twitch)
    pubsub.start()
    # you can either start listening before or after you started pubsub.
    uuid = pubsub.listen_whispers(user_id, callback_whisper)
    input('press ENTER to close...')
    # you do not need to unlisten to topics before stopping but you can listen and unlisten at any moment you want
    pubsub.unlisten(uuid)
    pubsub.stop()

********************
Class Documentation:
********************
"""

from .twitch import Twitch
from .types import *
from .helper import get_uuid, make_enum, TWITCH_PUB_SUB_URL
import asyncio
import websockets
import threading
import json
from random import randrange
import datetime
from logging import getLogger, Logger
from typing import Callable, List, Dict
from uuid import UUID
from time import sleep


class PubSub:
    """The PubSub client

    :var int ping_frequency: with which frequency in seconds a ping command is send.
                                You probably don't want to change this.
                                This should never be shorter than 12 + `ping_jitter` seconds to avoid problems
                                with the pong timeout.
                                |default| :code:`120`
    :var int ping_jitter: time in seconds added or subtracted from `ping_frequency`.
                             You probably don't want to change this.
                             |default| :code:`4`
    :var int listen_confirm_timeout: maximum time in seconds waited for a listen confirm.
                                        |default| :code:`30`
    """

    ping_frequency: int = 120
    ping_jitter: int = 4
    listen_confirm_timeout: int = 30
    reconnect_delay_steps: List[int] = [1, 2, 4, 8, 16, 32, 64, 128]

    __twitch: Twitch = None
    __connection = None
    __socket_thread: threading.Thread = None
    __running: bool = False
    __socket_loop = None
    __topics: dict = {}
    __startup_complete: bool = False

    __tasks = None

    __waiting_for_pong: bool = False
    __logger: Logger = None
    __nonce_waiting_confirm: dict = {}

    def __init__(self, twitch: Twitch):
        self.__twitch = twitch
        self.__logger = getLogger('twitchAPI.pubsub')

    def start(self) -> None:
        """
        Start the PubSub Client

        :raises RuntimeError: if already started
        """
        if self.__running:
            raise RuntimeError('already started')
        self.__startup_complete = False
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
        while not self.__startup_complete:
            sleep(0.01)

    def stop(self) -> None:
        """
        Stop the PubSub Client

        :raises RuntimeError: if the client is not running
        """

        if not self.__running:
            raise RuntimeError('not running')
        self.__startup_complete = False
        self.__running = False
        for task in self.__tasks:
            task.cancel()
        self.__socket_loop.call_soon_threadsafe(self.__socket_loop.stop)
        self.__socket_thread.join()

###########################################################################################
# Internal
###########################################################################################

    async def __connect(self, is_startup=False):
        if self.__connection is not None and self.__connection.open:
            await self.__connection.close()
        retry = 0
        need_retry = True
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self.__connection = await websockets.connect(TWITCH_PUB_SUB_URL, loop=self.__socket_loop)
            except websockets.InvalidHandshake:
                self.__logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]}s...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException('cant connect')

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

    def __generic_listen(self, key, callback_func, required_scopes: List[AuthScope]) -> UUID:
        for scope in required_scopes:
            if scope not in self.__twitch.get_user_auth_scope():
                raise MissingScopeException(str(scope))
        uuid = get_uuid()
        if key not in self.__topics.keys():
            self.__topics[key] = {'subs': {}}
        self.__topics[key]['subs'][uuid] = callback_func
        if self.__startup_complete:
            asyncio.get_event_loop().run_until_complete(self.__send_listen(str(uuid), [key]))
        return uuid

###########################################################################################
# Asyncio Tasks
###########################################################################################

    async def __task_initial_listen(self):
        self.__startup_complete = True
        if len(list(self.__topics.keys())) > 0:
            uuid = str(get_uuid())
            await self.__send_listen(uuid, list(self.__topics.keys()))

    async def __task_heartbeat(self):
        while True:
            next_heartbeat = datetime.datetime.utcnow() + \
                             datetime.timedelta(seconds=randrange(self.ping_frequency - self.ping_jitter,
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

    async def __task_receive(self):
        async for message in self.__connection:
            data = json.loads(message)
            switcher: Dict[str, Callable] = {
                'pong': self.__handle_pong,
                'reconnect': self.__handle_reconnect,
                'response': self.__handle_response,
                'message': self.__handle_message
            }
            handler = switcher.get(data.get('type', '').lower(),
                                   self.__handle_unknown)
            self.__socket_loop.create_task(handler(data))

###########################################################################################
# Handler
###########################################################################################

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

###########################################################################################
# Listener
###########################################################################################

    def unlisten(self, uuid: UUID) -> None:
        """
        Stop listening to a specific Topic subscription.

        :param ~uuid.UUID uuid: The UUID of the subscription you want to stop listening to
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the server response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the unsubscription is not confirmed in the time set by
                `listen_confirm_timeout`
        """
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
        """
        You are notified when anyone whispers the specified user or the specified user whispers to anyone.\n
        Requires the :const:`twitchAPI.types.AuthScope.WHISPERS_READ` AuthScope.\n

        :param str user_id: ID of the User
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'whispers.{user_id}', callback_func, [AuthScope.WHISPERS_READ])

    def listen_bits_v1(self,
                       channel_id: str,
                       callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        You are notified when anyone cheers in the specified channel.\n
        Requires the :const:`twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'channel-bits-events-v1.{channel_id}', callback_func, [AuthScope.BITS_READ])

    def listen_bits(self,
                    channel_id: str,
                    callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        You are notified when anyone cheers in the specified channel.\n
        Requires the :const:`twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'channel-bits-events-v2.{channel_id}', callback_func, [AuthScope.BITS_READ])

    def listen_bits_badge_notification(self,
                                       channel_id: str,
                                       callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        You are notified when a user earns a new Bits badge in the given channel,
        and chooses to share the notification with chat.\n
        Requires the :const:`twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'channel-bits-badge-unlocks.{channel_id}', callback_func, [AuthScope.BITS_READ])

    def listen_channel_points(self,
                              channel_id: str,
                              callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        You are notified when a custom reward is redeemed in the channel.\n
        Requires the :const:`twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` AuthScope.\n

        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'channel-points-channel-v1.{channel_id}',
                                     callback_func,
                                     [AuthScope.CHANNEL_READ_REDEMPTIONS])

    def listen_channel_subscriptions(self,
                                     channel_id: str,
                                     callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        You are notified when anyone subscribes (first month), resubscribes (subsequent months),
        or gifts a subscription to a channel. Subgift subscription messages contain recipient information.\n
        Requires the :const:`twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` AuthScope.\n

        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'channel-subscribe-events-v1.{channel_id}',
                                     callback_func,
                                     [AuthScope.CHANNEL_READ_SUBSCRIPTIONS])

    def listen_chat_moderator_actions(self,
                                      user_id: str,
                                      channel_id: str,
                                      callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        Supports moderators listening to the topic, as well as users listening to the topic to receive their own events.
        Examples of moderator actions are bans, unbans, timeouts, deleting messages,
        changing chat mode (followers-only, subs-only), changing AutoMod levels, and adding a mod.\n
        Requires the :const:`twitchAPI.types.AuthScope.CHANNEL_MODERATE` AuthScope.\n

        :param str user_id: ID of the User
        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'chat_moderator_actions.{user_id}.{channel_id}',
                                     callback_func,
                                     [AuthScope.CHANNEL_MODERATE])

    def listen_automod_queue(self,
                             moderator_id: str,
                             channel_id: str,
                             callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        AutoMod flags a message as potentially inappropriate, and when a moderator takes action on a message.\n
        Requires the :const:`twitchAPI.types.AuthScope.CHANNEL_MODERATE` AuthScope.\n

        :param str moderator_id: ID of the Moderator
        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'automod-queue.{moderator_id}.{channel_id}',
                                     callback_func,
                                     [AuthScope.CHANNEL_MODERATE])

    def listen_user_moderation_notifications(self,
                                             user_id: str,
                                             channel_id: str,
                                             callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        A user’s message held by AutoMod has been approved or denied.\n
        Requires the :const:`twitchAPI.types.AuthScope.CHAT_READ` AuthScope.\n

        :param str user_id: ID of the User
        :param str channel_id: ID of the Channel
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :return: UUID of this subscription
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return self.__generic_listen(f'user-moderation-notifications.{user_id}.{channel_id}',
                                     callback_func,
                                     [AuthScope.CHAT_READ])

    def listen_undocumented_topic(self,
                                  topic: str,
                                  callback_func: Callable[[UUID, dict], None]) -> UUID:
        """
        Listen to one of the many undocumented PubSub topics.

        Make sure that you have the required AuthScope for your topic set, since this lib can not check it for you!

        .. warning:: Using a undocumented topic can break at any time, use at your own risk!

        :param str topic: the topic string
        :param Callable[[~uuid.UUID,dict],None] callback_func: Function called on event
        :rtype: ~uuid.UUID
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid or does not have the required AuthScope
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by
                `listen_confirm_timeout`
        """
        self.__logger.warning(f"using undocumented topic {topic}")
        return self.__generic_listen(topic, callback_func, [])
