#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
EventSub Websocket
------------------

.. warning:: Rework in progress, docs not accurate

"""
import asyncio
import datetime
import json
import threading
from asyncio import CancelledError
from time import sleep
from typing import Optional, List, Dict, Callable

import aiohttp
from aiohttp import ClientSession

from .base import EventSubBase


__all__ = ['EventSubWebsocket']

from .. import Twitch
from ..helper import TWITCH_EVENT_SUB_WEBSOCKET_URL, TWITCH_API_BASE_URL
from ..types import AuthType, UnauthorizedException, TwitchBackendException, EventSubSubscriptionConflict, EventSubSubscriptionError, \
    TwitchAuthorizationException


class Session:

    def __init__(self, data: dict):
        self.id: str = data.get('id')
        self.keepalive_timeout_seconds: int = data.get('keepalive_timeout_seconds')
        self.status: str = data.get('status')
        self.reconnect_url: str = data.get('reconnect_url')


class EventSubWebsocket(EventSubBase):
    
    def __init__(self, twitch: Twitch, connection_url: Optional[str] = None):
        super().__init__(twitch)
        self.connection_url: str = connection_url if connection_url is not None else TWITCH_EVENT_SUB_WEBSOCKET_URL
        self.session: Optional[Session] = None
        self._running: bool = False
        self._socket_thread = None
        self._startup_complete: bool = False
        self._socket_loop = None
        self._ready: bool = False
        self._closing: bool = False
        self._connection = None
        self._session = None
        self._reconnect_timeout: datetime.datetime = None
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
            'session_id': self.session.id
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
            r_data = await self._api_post_request(session, TWITCH_API_BASE_URL + 'eventsub/subscriptions', data=data)
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
        return sub_id

    async def _connect(self, is_startup: bool = False):
        if is_startup:
            self.logger.debug('connectiong...')
        else:
            self.logger.debug('reconnecting...')
        self._reconnect_timeout = None
        if self._connection is not None and not self._connection.closed:
            await self._connection.close()
        retry = 0
        need_retry = True
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._twitch.session_timeout)
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self._connection = await self._session.ws_connect(self.connection_url)
            except Exception:
                self.logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]} seconds...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException(f'can\'t connect to EventSub websocket {self.connection_url}')
        if not is_startup:
            await self._resubscribe()

    def _run_socket(self):
        self._socket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._socket_loop)

        self._socket_loop.run_until_complete(self._connect(is_startup=True))

        self._tasks = [
            asyncio.ensure_future(self._task_receive(), loop=self._socket_loop),
            asyncio.ensure_future(self._task_startup(), loop=self._socket_loop),
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

    async def _task_startup(self):
        while self.session is None:
            await asyncio.sleep(0.1)
        self._startup_complete = True

    async def _task_reconnect_handler(self):
        try:
            while not self._closing:
                await asyncio.sleep(0.1)
                if self._reconnect_timeout is None:
                    continue
                if self._reconnect_timeout <= datetime.datetime.now():
                    self.logger.warning('keepalive missed, connection lost. reconnecting...')
                    await self._connect(is_startup=False)
        except CancelledError:
            return

    async def _task_receive(self):
        handler: Dict[str, Callable] = {
            'session_welcome': self._handle_welcome,
            'session_keepalive': self._handle_keepalive,
            'notification': self._handle_notification
        }
        try:
            while not self._connection.closed:
                message = await self._connection.receive()
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
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.debug('websocket is closing')
                    if self._running:
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

    async def _resubscribe(self):
        # TODO resubscribe to all subscriptions on startup
        pass

    def _reset_timeout(self):
        self._reconnect_timeout = datetime.datetime.now() + datetime.timedelta(seconds=self.session.keepalive_timeout_seconds)

    async def _handle_welcome(self, data: dict):
        session = data.get('payload', {}).get('session', {})
        self.session = Session(session)
        self._reset_timeout()

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
        self._socket_loop.create_task(callback['callback'](_payload))
