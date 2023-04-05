#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
PubSub Client
-------------

This is a full implementation of the PubSub API of twitch.
PubSub enables you to subscribe to a topic, for updates (e.g., when a user cheers in a channel).

Read more about it on `the Twitch API Documentation <https://dev.twitch.tv/docs/pubsub>`__.

.. note:: You **always** need User Authentication while using this!

************
Code Example
************

.. code-block:: python

    from twitchAPI.pubsub import PubSub
    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.types import AuthScope
    from twitchAPI.oauth import UserAuthenticator
    import asyncio
    from pprint import pprint
    from uuid import UUID

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.WHISPERS_READ]
    TARGET_CHANNEL = 'teekeks42'

    async def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)


    async def run_example():
        # setting up Authentication and getting your user id
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, [AuthScope.WHISPERS_READ], force_verify=False)
        token, refresh_token = await auth.authenticate()
        # you can get your user auth token and user auth refresh token following the example in twitchAPI.oauth
        await twitch.set_user_authentication(token, [AuthScope.WHISPERS_READ], refresh_token)
        user = await first(twitch.get_users(logins=[TARGET_CHANNEL]))

        # starting up PubSub
        pubsub = PubSub(twitch)
        pubsub.start()
        # you can either start listening before or after you started pubsub.
        uuid = await pubsub.listen_whispers(user.id, callback_whisper)
        input('press ENTER to close...')
        # you do not need to unlisten to topics before stopping but you can listen and unlisten at any moment you want
        await pubsub.unlisten(uuid)
        pubsub.stop()
        await twitch.close()

    asyncio.run(run_example())


*******************
Class Documentation
*******************
"""
from asyncio import CancelledError

import aiohttp
from aiohttp import ClientSession

from .twitch import Twitch
from .types import *
from .helper import get_uuid, make_enum, TWITCH_PUB_SUB_URL
import asyncio
import threading
import json
from random import randrange
import datetime
from logging import getLogger, Logger
from uuid import UUID
from time import sleep

from typing import Callable, List, Dict, Awaitable, Optional

__all__ = ['PubSub']


CALLBACK_FUNC = Callable[[UUID, dict], Awaitable[None]]


class PubSub:
    """The PubSub client
    """

    def __init__(self, twitch: Twitch):
        """

        :param twitch:  A authenticated Twitch instance
        """
        self.__twitch: Twitch = twitch
        self.logger: Logger = getLogger('twitchAPI.pubsub')
        """The logger used for PubSub related log messages"""
        self.ping_frequency: int = 120
        """With which frequency in seconds a ping command is send. You probably don't want to change this. 
           This should never be shorter than 12 + `ping_jitter` seconds to avoid problems with the pong timeout. |default| :code:`120`"""
        self.ping_jitter: int = 4
        """time in seconds added or subtracted from `ping_frequency`. You probably don't want to change this. |default| :code:`4`"""
        self.listen_confirm_timeout: int = 30
        """maximum time in seconds waited for a listen confirm. |default| :code:`30`"""
        self.reconnect_delay_steps: List[int] = [1, 2, 4, 8, 16, 32, 64, 128]
        self.__connection = None
        self.__socket_thread: Optional[threading.Thread] = None
        self.__running: bool = False
        self.__socket_loop = None
        self.__topics: dict = {}
        self._session = None
        self.__startup_complete: bool = False
        self.__tasks = None
        self.__waiting_for_pong: bool = False
        self.__nonce_waiting_confirm: dict = {}
        self._closing = False

    def start(self) -> None:
        """
        Start the PubSub Client

        :raises RuntimeError: if already started
        """
        self.logger.debug('starting pubsub...')
        if self.__running:
            raise RuntimeError('already started')
        self.__startup_complete = False
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
        while not self.__startup_complete:
            sleep(0.01)
        self.logger.debug('pubsub started up!')

    async def _stop(self):
        for t in self.__tasks:
            t.cancel()
        await self.__connection.close()
        await self._session.close()
        await asyncio.sleep(0.25)
        self._closing = True

    def stop(self) -> None:
        """
        Stop the PubSub Client

        :raises RuntimeError: if the client is not running
        """

        if not self.__running:
            raise RuntimeError('not running')
        self.logger.debug('stopping pubsub...')
        self.__startup_complete = False
        self.__running = False
        f = asyncio.run_coroutine_threadsafe(self._stop(), self.__socket_loop)
        f.result()
        self.logger.debug('pubsub stopped!')
        self.__socket_thread.join()

    def is_connected(self) -> bool:
        """Returns your current connection status."""
        if self.__connection is None:
            return False
        return not self.__connection.closed

###########################################################################################
# Internal
###########################################################################################

    async def __connect(self, is_startup=False):
        self.logger.debug('connecting...')
        self._closing = False
        if self.__connection is not None and not self.__connection.closed:
            await self.__connection.close()
        retry = 0
        need_retry = True
        if self._session is None:
            self._session = ClientSession(timeout=self.__twitch.session_timeout)
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self.__connection = await self._session.ws_connect(TWITCH_PUB_SUB_URL)
            except Exception:
                self.logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]}s...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException('can\'t connect')

        if not self.__connection.closed and not is_startup:
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
        self.logger.debug(f'sending {"" if subscribe else "un"}listen for topics {str(topics)} with nonce {nonce}')
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
        self.logger.debug(f'sending message {json.dumps(msg_data)}')
        await self.__connection.send_str(json.dumps(msg_data))

    async def _keep_loop_alive(self):
        while not self._closing:
            await asyncio.sleep(0.1)

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

        self.__socket_loop.run_until_complete(self._keep_loop_alive())

    async def __generic_listen(self, key, callback_func, required_scopes: List[AuthScope]) -> UUID:
        if not asyncio.iscoroutinefunction(callback_func):
            raise ValueError('callback_func needs to be a async function which takes 2 arguments')
        for scope in required_scopes:
            if scope not in self.__twitch.get_user_auth_scope():
                raise MissingScopeException(str(scope))
        uuid = get_uuid()
        if key not in self.__topics.keys():
            self.__topics[key] = {'subs': {}}
        self.__topics[key]['subs'][uuid] = callback_func
        if self.__startup_complete:
            await self.__send_listen(str(uuid), [key])
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
        while not self._closing:
            next_heartbeat = datetime.datetime.utcnow() + \
                             datetime.timedelta(seconds=randrange(self.ping_frequency - self.ping_jitter,
                                                                  self.ping_frequency + self.ping_jitter,
                                                                  1))

            while datetime.datetime.utcnow() < next_heartbeat:
                await asyncio.sleep(1)
            self.logger.debug('send ping...')
            pong_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
            self.__waiting_for_pong = True
            await self.__send_message({'type': 'PING'})
            while self.__waiting_for_pong:
                if datetime.datetime.utcnow() > pong_timeout:
                    self.logger.info('did not receive pong in time, reconnecting...')
                    await self.__connect()
                    self.__waiting_for_pong = False
                await asyncio.sleep(1)

    async def __task_receive(self):
        try:
            while not self.__connection.closed:
                message = await self.__connection.receive()
                if message.type == aiohttp.WSMsgType.TEXT:
                    messages = message.data.split('\r\n')
                    for m in messages:
                        if len(m) == 0:
                            continue
                        self.logger.debug(f'received message {m}')
                        data = json.loads(m)
                        switcher: Dict[str, Callable] = {
                            'pong': self.__handle_pong,
                            'reconnect': self.__handle_reconnect,
                            'response': self.__handle_response,
                            'message': self.__handle_message
                        }
                        handler = switcher.get(data.get('type', '').lower(),
                                               self.__handle_unknown)
                        self.__socket_loop.create_task(handler(data))
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.debug('websocket is closing... trying to reestablish connection')
                    try:
                        await self._handle_base_reconnect()
                    except TwitchBackendException:
                        self.logger.exception('Connection to websocket lost and unable to reestablish connection!')
                        break
                    break
                elif message.type == aiohttp.WSMsgType.ERROR:
                    self.logger.warning('error in websocket')
                    break
        except CancelledError:
            return

###########################################################################################
# Handler
###########################################################################################

    async def _handle_base_reconnect(self):
        await self.__connect(is_startup=False)

    # noinspection PyUnusedLocal
    async def __handle_pong(self, data):
        self.__waiting_for_pong = False
        self.logger.debug('received pong')

    # noinspection PyUnusedLocal
    async def __handle_reconnect(self, data):
        self.logger.info('received reconnect command, reconnecting now...')
        await self.__connect()

    async def __handle_response(self, data):
        error = make_enum(data.get('error'),
                          PubSubResponseError,
                          PubSubResponseError.UNKNOWN)
        self.logger.debug(f'got response for nonce {data.get("nonce")}: {str(error)}')
        self.__nonce_waiting_confirm[data.get('nonce')]['error'] = error
        self.__nonce_waiting_confirm[data.get('nonce')]['received'] = True

    async def __handle_message(self, data):
        topic_data = self.__topics.get(data.get('data', {}).get('topic', ''), None)
        msg_data = json.loads(data.get('data', {}).get('message', '{}'))
        if topic_data is not None:
            for uuid, sub in topic_data.get('subs', {}).items():
                asyncio.ensure_future(sub(uuid, msg_data))

    async def __handle_unknown(self, data):
        self.logger.warning('got message of unknown type: ' + str(data))

###########################################################################################
# Listener
###########################################################################################

    async def unlisten(self, uuid: UUID) -> None:
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
            await self.__send_listen(str(uuid), clear_topics, subscribe=False)
        if len(clear_topics) > 0:
            for topic in clear_topics:
                self.__topics.pop(topic)

    async def listen_whispers(self,
                              user_id: str,
                              callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when anyone whispers the specified user or the specified user whispers to anyone.\n
        Requires the :const:`~twitchAPI.types.AuthScope.WHISPERS_READ` AuthScope.\n

        :param user_id: ID of the User
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'whispers.{user_id}', callback_func, [AuthScope.WHISPERS_READ])

    async def listen_bits_v1(self,
                             channel_id: str,
                             callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when anyone cheers in the specified channel.\n
        Requires the :const:`~twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'channel-bits-events-v1.{channel_id}', callback_func, [AuthScope.BITS_READ])

    async def listen_bits(self,
                          channel_id: str,
                          callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when anyone cheers in the specified channel.\n
        Requires the :const:`~twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'channel-bits-events-v2.{channel_id}', callback_func, [AuthScope.BITS_READ])

    async def listen_bits_badge_notification(self,
                                             channel_id: str,
                                             callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when a user earns a new Bits badge in the given channel,
        and chooses to share the notification with chat.\n
        Requires the :const:`~twitchAPI.types.AuthScope.BITS_READ` AuthScope.\n

        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'channel-bits-badge-unlocks.{channel_id}', callback_func, [AuthScope.BITS_READ])

    async def listen_channel_points(self,
                                    channel_id: str,
                                    callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when a custom reward is redeemed in the channel.\n
        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` AuthScope.\n

        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'channel-points-channel-v1.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHANNEL_READ_REDEMPTIONS])

    async def listen_channel_subscriptions(self,
                                           channel_id: str,
                                           callback_func: CALLBACK_FUNC) -> UUID:
        """
        You are notified when anyone subscribes (first month), resubscribes (subsequent months),
        or gifts a subscription to a channel. Subgift subscription messages contain recipient information.\n
        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` AuthScope.\n

        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'channel-subscribe-events-v1.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHANNEL_READ_SUBSCRIPTIONS])

    async def listen_chat_moderator_actions(self,
                                            user_id: str,
                                            channel_id: str,
                                            callback_func: CALLBACK_FUNC) -> UUID:
        """
        Supports moderators listening to the topic, as well as users listening to the topic to receive their own events.
        Examples of moderator actions are bans, unbans, timeouts, deleting messages,
        changing chat mode (followers-only, subs-only), changing AutoMod levels, and adding a mod.\n
        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` AuthScope.\n

        :param user_id: ID of the User
        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'chat_moderator_actions.{user_id}.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHANNEL_MODERATE])

    async def listen_automod_queue(self,
                                   moderator_id: str,
                                   channel_id: str,
                                   callback_func: CALLBACK_FUNC) -> UUID:
        """
        AutoMod flags a message as potentially inappropriate, and when a moderator takes action on a message.\n
        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` AuthScope.\n

        :param moderator_id: ID of the Moderator
        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'automod-queue.{moderator_id}.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHANNEL_MODERATE])

    async def listen_user_moderation_notifications(self,
                                                   user_id: str,
                                                   channel_id: str,
                                                   callback_func: CALLBACK_FUNC) -> UUID:
        """
        A user’s message held by AutoMod has been approved or denied.\n
        Requires the :const:`~twitchAPI.types.AuthScope.CHAT_READ` AuthScope.\n

        :param user_id: ID of the User
        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'user-moderation-notifications.{user_id}.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHAT_READ])

    async def listen_low_trust_users(self,
                                     moderator_id: str,
                                     channel_id: str,
                                     callback_func: CALLBACK_FUNC) -> UUID:
        """The broadcaster or a moderator updates the low trust status of a user,
        or a new message has been sent in chat by a potential ban evader or a bans shared user.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` AuthScope.\n

        :param moderator_id: ID of the moderator
        :param channel_id: ID of the Channel
        :param callback_func: Function called on event
        :return: UUID of this subscription
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        :raises ~twitchAPI.types.MissingScopeException: if required AuthScope is missing from Token
        """
        return await self.__generic_listen(f'low-trust-users.{moderator_id}.{channel_id}',
                                           callback_func,
                                           [AuthScope.CHANNEL_MODERATE])

    async def listen_undocumented_topic(self,
                                        topic: str,
                                        callback_func: CALLBACK_FUNC) -> UUID:
        """
        Listen to one of the many undocumented PubSub topics.

        Make sure that you have the required AuthScope for your topic set, since this lib can not check it for you!

        .. warning:: Using a undocumented topic can break at any time, use at your own risk!

        :param topic: the topic string
        :param callback_func: Function called on event
        :raises ~twitchAPI.types.TwitchAuthorizationException: if Token is not valid or does not have the required AuthScope
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch Server has a problem
        :raises ~twitchAPI.types.TwitchAPIException: if the subscription response is something else than suspected
        :raises ~twitchAPI.types.PubSubListenTimeoutException: if the subscription is not confirmed in the time set by `listen_confirm_timeout`
        """
        self.logger.warning(f"using undocumented topic {topic}")
        return await self.__generic_listen(topic, callback_func, [])
