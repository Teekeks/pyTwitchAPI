#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
import asyncio
import hashlib
import hmac
import threading
from random import choice
from string import ascii_lowercase
from ssl import SSLContext
from time import sleep
from typing import Optional, Union
import datetime

from aiohttp import web, ClientSession

from .base import EventSubBase
from .. import Twitch
from ..helper import TWITCH_API_BASE_URL
from ..types import TwitchBackendException, EventSubSubscriptionConflict, EventSubSubscriptionError, EventSubSubscriptionTimeout, \
    TwitchAuthorizationException

__all__ = ['EventSubWebhook']


class EventSubWebhook(EventSubBase):

    def __init__(self,
                 callback_url: str,
                 port: int,
                 twitch: Twitch,
                 ssl_context: Optional[SSLContext] = None,
                 host_binding: str = '0.0.0.0'):
        """
        :param callback_url: The full URL of the webhook.
        :param port: the port on which this webhook should run
        :param twitch: a app authenticated instance of :const:`~twitchAPI.twitch.Twitch`
        :param ssl_context: optional ssl context to be used |default| :code:`None`
        """
        super().__init__(twitch)
        self.callback_url: str = callback_url
        """The full URL of the webhook."""
        self.secret: str = ''.join(choice(ascii_lowercase) for _ in range(20))
        """A random secret string. Set this for added security. |default| :code:`A random 20 character long string`"""
        self.wait_for_subscription_confirm: bool = True
        """Set this to false if you don't want to wait for a subscription confirm. |default| :code:`True`"""
        self.wait_for_subscription_confirm_timeout: int = 30
        """Max time in seconds to wait for a subscription confirmation. Only used if ``wait_for_subscription_confirm`` is set to True. 
            |default| :code:`30`"""

        self._port: int = port
        self._host: str = host_binding
        self.__running = False
        self._startup_complete = False
        self.unsubscribe_on_stop: bool = True
        """Unsubscribe all currently active Webhooks on calling :const:`~twitchAPI.eventsub.EventSub.stop()` |default| :code:`True`"""

        self._closing = False
        self.__ssl_context: Optional[SSLContext] = ssl_context
        self.__active_webhooks = {}
        self.__hook_thread: Union['threading.Thread', None] = None
        self.__hook_loop: Union['asyncio.AbstractEventLoop', None] = None
        self.__hook_runner: Union['web.AppRunner', None] = None
        if not self.callback_url.startswith('https'):
            raise RuntimeError('HTTPS is required for authenticated webhook.\n'
                               + 'Either use non authenticated webhook or use a HTTPS proxy!')

    def __build_runner(self):
        hook_app = web.Application()
        hook_app.add_routes([web.post('/callback', self.__handle_callback),
                             web.get('/', self.__handle_default)])
        return web.AppRunner(hook_app)

    def __run_hook(self, runner: 'web.AppRunner'):
        self.__hook_runner = runner
        self.__hook_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__hook_loop)
        self.__hook_loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, str(self._host), self._port, ssl_context=self.__ssl_context)
        self.__hook_loop.run_until_complete(site.start())
        self.logger.info('started twitch API event sub on port ' + str(self._port))
        self._startup_complete = True
        self.__hook_loop.run_until_complete(self._keep_loop_alive())

    async def _keep_loop_alive(self):
        while not self._closing:
            await asyncio.sleep(0.1)

    def start(self):
        """Starts the EventSub client

        :rtype: None
        :raises RuntimeError: if EventSub is already running
        """
        if self.__running:
            raise RuntimeError('already started')
        self.__hook_thread = threading.Thread(target=self.__run_hook, args=(self.__build_runner(),))
        self.__running = True
        self._startup_complete = False
        self._closing = False
        self.__hook_thread.start()
        while not self._startup_complete:
            sleep(0.1)

    async def stop(self):
        """Stops the EventSub client

        This also unsubscribes from all known subscriptions if unsubscribe_on_stop is True

        :rtype: None
        """
        self.logger.debug('shutting down eventsub')
        if self.__hook_runner is not None and self.unsubscribe_on_stop:
            await self.unsubscribe_all_known()
        # ensure all client sessions are closed
        await asyncio.sleep(0.25)
        self._closing = True
        # cleanly shut down the runner
        await self.__hook_runner.shutdown()
        await self.__hook_runner.cleanup()
        self.__hook_runner = None
        self.__running = False
        self.logger.debug('eventsub shut down')

    def _get_transport(self):
        return {
            'method': 'webhook',
            'callback': f'{self.callback_url}/callback',
            'secret': self.secret
        }

    def _build_request_header(self):
        token = self._twitch.get_app_token()
        if token is None:
            raise TwitchAuthorizationException('no Authorization set!')
        return {
            'Client-ID': self._twitch.app_id,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    async def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback) -> str:
        """"Subscribe to Twitch Topic"""
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
        if self.wait_for_subscription_confirm:
            timeout = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=self.wait_for_subscription_confirm_timeout)
            while timeout >= datetime.datetime.utcnow():
                if self._callbacks[sub_id]['active']:
                    return sub_id
                await asyncio.sleep(0.01)
            self._callbacks.pop(sub_id, None)
            raise EventSubSubscriptionTimeout()
        return sub_id

    async def _verify_signature(self, request: 'web.Request') -> bool:
        expected = request.headers['Twitch-Eventsub-Message-Signature']
        hmac_message = request.headers['Twitch-Eventsub-Message-Id'] + \
            request.headers['Twitch-Eventsub-Message-Timestamp'] + await request.text()
        sig = 'sha256=' + hmac.new(bytes(self.secret, 'utf-8'),
                                   msg=bytes(hmac_message, 'utf-8'),
                                   digestmod=hashlib.sha256).hexdigest().lower()
        return sig == expected

    # noinspection PyUnusedLocal
    @staticmethod
    async def __handle_default(request: 'web.Request'):
        return web.Response(text="pyTwitchAPI EventSub")

    async def __handle_challenge(self, request: 'web.Request', data: dict):
        self.logger.debug(f'received challenge for subscription {data.get("subscription").get("id")}')
        if not await self._verify_signature(request):
            self.logger.warning(f'message signature is not matching! Discarding message')
            return web.Response(status=403)
        await self._activate_callback(data.get('subscription').get('id'))
        return web.Response(text=data.get('challenge'))

    async def __handle_callback(self, request: 'web.Request'):
        data: dict = await request.json()
        if data.get('challenge') is not None:
            return await self.__handle_challenge(request, data)
        sub_id = data.get('subscription', {}).get('id')
        callback = self._callbacks.get(sub_id)
        if callback is None:
            self.logger.error(f'received event for unknown subscription with ID {sub_id}')
        else:
            if not await self._verify_signature(request):
                self.logger.warning(f'message signature is not matching! Discarding message')
                return web.Response(status=403)
            self.__hook_loop.create_task(callback['callback'](data))
        return web.Response(status=200)
