#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Full Implementation of the Twitch EventSub
-----------------------------------------

In Progress

********************
Class Documentation:
********************
"""
import datetime
from typing import Union, Tuple, Callable, List, Optional
from .helper import build_url, TWITCH_API_BASE_URL, get_uuid, get_json, make_fields_datetime, fields_to_enum
from .helper import extract_uuid_str_from_url
from .types import *
import requests
from aiohttp import web
import threading
import asyncio
from uuid import UUID
from logging import getLogger, Logger
import time
from .twitch import Twitch
from concurrent.futures._base import CancelledError
from ssl import SSLContext
from pprint import pprint
from .types import EventSubSubscriptionTimeout, EventSubSubscriptionConflict


class EventSub:
    """EventSub integration for the Twitch Helix API.

    :param str callback_url: The full URL of the webhook.
    :param str api_client_id: The id of your API client
    :param int port: the port on which this webhook should run
    :param ~ssl.SSLContext ssl_context: optional ssl context to be used |default| :code:`None`
    :var str secret: A random secret string. Set this for added security.
    :var str callback_url: The full URL of the webhook.
    :var bool wait_for_subscription_confirm: Set this to false if you dont want to wait for a subscription confirm.
                    |default| :code:`True`
    :var int wait_for_subscription_confirm_timeout: Max time in seconds to wait for a subscription confirmation.
                    Only used if ``wait_for_subscription_confirm`` is set to True. |default| :code:`30`
    :var bool unsubscribe_on_stop: Unsubscribe all currently active Webhooks on calling `stop()`
                    |default| :code:`True`
    """

    secret = "asdg6456di"
    callback_url = None
    wait_for_subscription_confirm: bool = True
    wait_for_subscription_confirm_timeout: int = 30
    unsubscribe_on_stop: bool = True
    _port: int = 80
    _host: str = '0.0.0.0'
    __twitch: Twitch = None
    __ssl_context = None
    __client_id = None
    __running = False
    __callbacks = {}
    __active_webhooks = {}
    __authenticate: bool = False
    __hook_thread: Union['threading.Thread', None] = None
    __hook_loop: Union['asyncio.AbstractEventLoop', None] = None
    __hook_runner: Union['web.AppRunner', None] = None
    __logger: Logger = None

    def __init__(self, callback_url: str, api_client_id: str, port: int, ssl_context: Optional[SSLContext] = None):
        self.callback_url = callback_url
        self.__client_id = api_client_id
        self._port = port
        self.__ssl_context = ssl_context
        self.__logger = getLogger('twitchAPI.webhook')

    def authenticate(self, twitch: Twitch) -> None:
        """Set authentication for the Webhook. Can be either a app or user token.

        :param ~twitchAPI.twitch.Twitch twitch: a authenticated instance of :class:`~twitchAPI.twitch.Twitch`
        :rtype: None
        :raises RuntimeError: if the callback URL does not use HTTPS
        """
        self.__authenticate = True
        self.__twitch = twitch
        if not self.callback_url.startswith('https'):
            raise RuntimeError('HTTPS is required for authenticated webhook.\n'
                               + 'Either use non authenticated webhook or use a HTTPS proxy!')

    def __build_runner(self):
        hook_app = web.Application()
        hook_app.add_routes([web.post('/callback', self.__handle_callback),
                             web.get('/', self.__handle_default)])
        hook_runner = web.AppRunner(hook_app)
        return hook_runner

    def __run_hook(self, runner: 'web.AppRunner'):
        self.__hook_runner = runner
        self.__hook_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__hook_loop)
        self.__hook_loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, str(self._host), self._port, ssl_context=self.__ssl_context)
        self.__hook_loop.run_until_complete(site.start())
        self.__logger.info('started twitch API event sub on port ' + str(self._port))
        try:
            self.__hook_loop.run_forever()
        except (CancelledError, asyncio.CancelledError):
            pass

    def start(self):
        """Starts the EventSub client

        :rtype: None
        :raises RuntimeError: if EventSub is already running
        """
        if self.__running:
            raise RuntimeError('already started')
        self.__hook_thread = threading.Thread(target=self.__run_hook, args=(self.__build_runner(),))
        self.__running = True
        self.__hook_thread.start()

    def stop(self):
        """Stops the Webhook

        Please make sure to unsubscribe from all subscriptions!

        :rtype: None
        """
        if self.__hook_runner is not None:
            if self.unsubscribe_on_stop:
                all_keys = list(self.__active_webhooks.keys())
            self.__hook_loop.call_soon_threadsafe(self.__hook_loop.stop)
            self.__hook_runner = None
            self.__hook_thread.join()
            self.__running = False

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    def __build_request_header(self):
        headers = {
            "Client-ID": self.__client_id,
            "Content-Type": "application/json"
        }
        if self.__authenticate:
            token = self.__twitch.get_used_token()
            if token is None:
                raise TwitchAuthorizationException('no Authorization set!')
            headers['Authorization'] = "Bearer " + token
        return headers

    def __api_post_request(self, url: str, data: Union[dict, None] = None):
        headers = self.__build_request_header()
        if data is None:
            return requests.post(url, headers=headers)
        else:
            return requests.post(url, headers=headers, json=data)

    def __api_get_request(self, url: str):
        headers = self.__build_request_header()
        return requests.get(url, headers=headers)

    def __api_delete_request(self, url: str):
        headers = self.__build_request_header()
        return requests.delete(url, headers=headers)

    def __add_callback(self, c_id: str, callback):
        self.__callbacks[c_id] = {'id': c_id, 'callback': callback, 'active': False}

    def __activate_callback(self, c_id: str):
        self.__callbacks[c_id]['active'] = True

    def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback):
        """"Subscribe to Twitch Topic"""
        # self.__logger.debug(f'{mode} to topic {topic_url} for {callback_path}')
        self.__logger.debug(f'subscribe to {sub_type} version {sub_version} with condition {condition}')
        data = {
            'type': sub_type,
            'version': sub_version,
            'condition': condition,
            'transport': {
                'method': 'webhook',
                'callback': f'{self.callback_url}/callback',
                'secret': self.secret
            }
        }
        result = self.__api_post_request(TWITCH_API_BASE_URL + 'eventsub/subscriptions', data=data).json()
        if result.get('error', '').lower() == 'conflict':
            raise EventSubSubscriptionConflict(result.get('message', ''))
        self.__add_callback(result['data'][0]['id'], callback)
        if self.wait_for_subscription_confirm:
            timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.wait_for_subscription_confirm_timeout)
            while timeout >= datetime.datetime.utcnow():
                if self.__callbacks[result['data'][0]['id']]['active']:
                    return
                else:
                    asyncio.sleep(0.01)
            raise EventSubSubscriptionTimeout()
    # ==================================================================================================================
    # HANDLERS
    # ==================================================================================================================

    async def __handle_default(self, request: 'web.Request'):
        return web.Response(text="pyTwitchAPI EventSub")

    async def __handle_challenge(self, request: 'web.Request', data: dict):
        self.__logger.debug(f'received challenge for subscription {data.get("subscription").get("id")}')
        self.__activate_callback(data.get('subscription').get('id'))
        return web.Response(text=data.get('challenge'))

    async def __handle_callback(self, request: 'web.Request'):
        data: dict = await request.json()
        if data.get('challenge') is not None:
            return await self.__handle_challenge(request, data)
        else:
            sub_id = data.get('subscription', {}).get('id')
            callback = self.__callbacks.get(sub_id)
            if callback is None:
                self.__logger.error(f'received event for unknown subscription with ID {sub_id}')
            else:
                await callback['callback'](data.get('event', {}))
            pass

    def listen_channel_follow(self, broadcaster_user_id: str, callback):
        self._subscribe('channel.follow', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)
