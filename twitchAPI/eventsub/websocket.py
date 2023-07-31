#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
EventSub Websocket
------------------

.. warning:: Rework in progress, docs not accurate

"""
import asyncio
import datetime
import json
import logging
import threading
from asyncio import CancelledError
from functools import partial
from logging import getLogger, Logger
from time import sleep
from typing import Optional, List, Dict, Callable

import aiohttp
from aiohttp import ClientSession, WSMessage

from .base import EventSubBase


__all__ = ['EventSubWebsocket']

from .. import Twitch
from ..helper import TWITCH_EVENT_SUB_WEBSOCKET_URL, TWITCH_API_BASE_URL, done_task_callback
from ..types import AuthType, UnauthorizedException, TwitchBackendException, EventSubSubscriptionConflict, EventSubSubscriptionError, \
    TwitchAuthorizationException


class Session:

    def __init__(self, data: dict):
        self.id: str = data.get('id')
        self.keepalive_timeout_seconds: int = data.get('keepalive_timeout_seconds')
        self.status: str = data.get('status')
        self.reconnect_url: str = data.get('reconnect_url')


class EventSubWebsocket(EventSubBase):
    
    def __init__(self,
                 twitch: Twitch,
                 connection_url: Optional[str] = None,
                 subscription_url: Optional[str] = None,
                 callback_loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        :param twitch: The Twitch instance to be used
        :param connection_url: Alternative connection URL, usefull for development with the twitch-cli
        :param subscription_url: Alternative subscription URL, usefull for development with the twitch-cli
        :param callback_loop: The asyncio eventloop to be used for callbacks. Set this if you
        """
        super().__init__(twitch)
        self.logger.name = 'twitchAPI.eventsub.websocket'
        self.subscription_url: Optional[str] = subscription_url
        if self.subscription_url is not None and self.subscription_url[-1] != '/':
            self.subscription_url += '/'
        self.connection_url: str = connection_url if connection_url is not None else TWITCH_EVENT_SUB_WEBSOCKET_URL
        self.active_session: Optional[Session] = None
        self._running: bool = False
        self._socket_thread = None
        self._startup_complete: bool = False
        self._socket_loop = None
        self._ready: bool = False
        self._closing: bool = False
        self._connection = None
        self._session = None
        self._callback_loop = callback_loop
        self._is_reconnecting: bool = False
        self._active_subscriptions = {}
        self._task_callback = partial(done_task_callback, self.logger)
        self._reconnect_timeout: Optional[datetime.datetime] = None
        self.reconnect_delay_steps: List[int] = [0, 1, 2, 4, 8, 16, 32, 64, 128]

    def start(self):
        self.logger.debug('starting websocket EventSub...')
        if self._running:
            raise RuntimeError('EventSubWebsocket is already started!')
        if not self._twitch.has_required_auth(AuthType.USER, []):
            raise UnauthorizedException('Twitch needs user authentication')
        self._startup_complete = False
        self._ready = False
        self._closing = False
        self._socket_thread = threading.Thread(target=self._run_socket)
        self._running = True
        self._active_subscriptions = {}
        self._socket_thread.start()
        while not self._startup_complete:
            sleep(0.01)
        self.logger.debug('EventSubWebsocket started up!')

    async def stop(self):
        if not self._running:
            raise RuntimeError('EventSubWebsocket is not running')
        self.logger.debug('stopping websocket EventSub...')
        self._startup_complete = False
        self._running = False
        self._ready = False
        f = asyncio.run_coroutine_threadsafe(self._stop(), self._socket_loop)
        f.result()

    def _get_transport(self):
        return {
            'method': 'websocket',
            'session_id': self.active_session.id
        }

    async def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback) -> str:
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError('callback needs to be a async function which takes one parameter')
        self.logger.debug(f'subscribe to {sub_type} version {sub_version} with condition {condition}')
        data = {
            'type': sub_type,
            'version': sub_version,
            'condition': condition,
            'transport': self._get_transport()
        }
        async with ClientSession(timeout=self._twitch.session_timeout) as session:
            sub_base = self.subscription_url if self.subscription_url is not None else self._twitch.base_url
            r_data = await self._api_post_request(session, sub_base + 'eventsub/subscriptions', data=data)
            result = await r_data.json()
        error = result.get('error')
        if r_data.status == 500:
            raise TwitchBackendException(error)
        if error is not None:
            if error.lower() == 'conflict':
                raise EventSubSubscriptionConflict(result.get('message', ''))
            raise EventSubSubscriptionError(result.get('message'))
        sub_id = result['data'][0]['id']
        self.logger.debug(f'subscription for {sub_type} version {sub_version} with condition {condition} has id {sub_id}')
        self._add_callback(sub_id, callback)
        self._callbacks[sub_id]['active'] = True
        self._active_subscriptions[sub_id] = {
            'sub_type': sub_type,
            'sub_version': sub_version,
            'condition': condition,
            'callback': callback
        }
        return sub_id

    async def _connect(self, is_startup: bool = False):
        _con_url = self.connection_url if self.active_session is None or self.active_session.reconnect_url is None else \
            self.active_session.reconnect_url
        if is_startup:
            self.logger.debug(f'connecting to {_con_url}...')
        else:
            self._is_reconnecting = True
            self.logger.debug(f'reconnecting using {_con_url}...')
        self._reconnect_timeout = None
        if self._connection is not None and not self._connection.closed:
            await self._connection.close()
            while not self._connection.closed:
                await asyncio.sleep(0.1)
        retry = 0
        need_retry = True
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._twitch.session_timeout)
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self._connection = await self._session.ws_connect(_con_url)
            except Exception:
                self.logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]} seconds...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException(f'can\'t connect to EventSub websocket {_con_url}')

    def _run_socket(self):
        self._socket_loop = asyncio.new_event_loop()
        if self._callback_loop is None:
            self._callback_loop = self._socket_loop
        asyncio.set_event_loop(self._socket_loop)

        self._socket_loop.run_until_complete(self._connect(is_startup=True))

        self._tasks = [
            asyncio.ensure_future(self._task_receive(), loop=self._socket_loop),
            asyncio.ensure_future(self._task_reconnect_handler(), loop=self._socket_loop)
        ]
        self._socket_loop.run_until_complete(self._keep_loop_alive())

    async def _stop(self):
        await self._connection.close()
        await self._session.close()
        await asyncio.sleep(0.25)
        self._connection = None
        self._session = None
        self._closing = True

    async def _keep_loop_alive(self):
        while not self._closing:
            await asyncio.sleep(0.1)

    async def _task_reconnect_handler(self):
        try:
            while not self._closing:
                await asyncio.sleep(0.1)
                if self._reconnect_timeout is None:
                    continue
                if self._reconnect_timeout <= datetime.datetime.now():
                    self.logger.warning('keepalive missed, connection lost. reconnecting...')
                    self._reconnect_timeout = None
                    await self._connect(is_startup=False)
        except CancelledError:
            return

    async def _task_receive(self):
        handler: Dict[str, Callable] = {
            'session_welcome': self._handle_welcome,
            'session_keepalive': self._handle_keepalive,
            'notification': self._handle_notification,
            'session_reconnect': self._handle_reconnect,
            'revocation': self._handle_revocation
        }
        try:
            while not self._closing:
                if self._connection.closed:
                    await asyncio.sleep(0.01)
                    continue
                message: WSMessage = await self._connection.receive()
                if message.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(message.data)
                    _type = data.get('metadata', {}).get('message_type')
                    _handler = handler.get(_type)
                    if _handler is not None:
                        asyncio.ensure_future(_handler(data))
                    # debug
                    else:
                        from pprint import pprint
                        pprint(data)
                elif message.type == aiohttp.WSMsgType.CLOSE:
                    msg_lookup = {
                        4000: "4000 - Internal server error",
                        4001: "4001 - Client sent inbound traffic",
                        4002: "4002 - Client failed ping-pong",
                        4003: "4003 - Connection unused, you have to create a subscription within 10 seconds",
                        4004: "4004 - Reconnect grace time expired",
                        4005: "4005 - Network timeout",
                        4006: "4006 - Network error",
                        4007: "4007 - Invalid reconnect"
                    }
                    self.logger.info(f'Websocket closing: {msg_lookup.get(message.data, f" {message.data} - Unknown")}')
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.debug('websocket is closing')
                    if self._running:
                        if self._is_reconnecting:
                            continue
                        try:
                            await self._connect(is_startup=False)
                        except TwitchBackendException:
                            self.logger.exception('Connection to EventSub websocket lost and unable to reestablish connection!')
                            break
                    else:
                        break
                elif message.type == aiohttp.WSMsgType.ERROR:
                    self.logger.warning('error in websocket: ' + str(self._connection.exception()))
                    break
        except CancelledError:
            return

    def _build_request_header(self):
        token = self._twitch.get_user_auth_token()
        if token is None:
            raise TwitchAuthorizationException('no Authorization set!')
        return {
            'Client-ID': self._twitch.app_id,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    async def _unsubscribe_hook(self, topic_id: str) -> bool:
        self._active_subscriptions.pop(topic_id, None)
        return True

    async def _resubscribe(self):
        self.logger.debug('resubscribe to all active subscriptions of this websocket...')
        subs = self._active_subscriptions.copy()
        self._active_subscriptions = {}
        for sub in subs.values():
            try:
                await self._subscribe(**sub)
            except:
                self.logger.exception('exception while resubscribing')
        self.logger.debug('done resubscribing!')

    def _reset_timeout(self):
        self._reconnect_timeout = datetime.datetime.now() + datetime.timedelta(seconds=self.active_session.keepalive_timeout_seconds*2)

    async def _handle_revocation(self, data: dict):
        # TODO: https://dev.twitch.tv/docs/eventsub/handling-websocket-events/#revocation-message
        pass

    async def _handle_reconnect(self, data: dict):
        session = data.get('payload', {}).get('session', {})
        self.active_session = Session(session)
        self.logger.debug(f'got request from websocket to reconnect')
        await self._connect(False)

    async def _handle_welcome(self, data: dict):
        session = data.get('payload', {}).get('session', {})
        _old_session = self.active_session.status if self.active_session is not None else None
        self.active_session = Session(session)
        self.logger.debug(f'new session id: {self.active_session.id}')
        self._reset_timeout()
        if self._is_reconnecting and _old_session != "reconnecting":
            await self._resubscribe()
        self._is_reconnecting = False
        self._startup_complete = True

    async def _handle_keepalive(self, data: dict):
        self.logger.debug('got session keep alive')
        self._reset_timeout()

    async def _handle_notification(self, data: dict):
        self._reset_timeout()
        _payload = data.get('payload', {})
        sub_id = _payload.get('subscription', {}).get('id')
        callback = self._callbacks.get(sub_id)
        if callback is None:
            self.logger.error(f'received event for unknown subscription with ID {sub_id}')
        else:
            t = self._callback_loop.create_task(callback['callback'](_payload))
            t.add_done_callback(self._task_callback)

