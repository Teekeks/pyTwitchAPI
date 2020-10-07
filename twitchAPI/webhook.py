#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
from typing import Union, Tuple, Callable
from .helper import build_url, TWITCH_API_BASE_URL, get_uuid, get_json, make_fields_datetime, fields_to_enum
from .types import *
import requests
from aiohttp import web
import threading
import asyncio
from uuid import UUID
import logging
import time


class TwitchWebHook:
    """Webhook integration for the Twitch Helix API.

    :param callback_url: The full URL of the webhook.
    :param api_client_id: The id of your API client
    :param port: the port on which this webhook should run
    :var secret: A random secret string. Set this for added security.
    :var callback_url: The full URL of the webhook.
    """

    secret = None
    __client_id = None
    __auth_token = None
    callback_url = None

    subscribe_least_seconds: int = 864000
    """The duration in seconds for how long you want to subscribe to webhhoks."""

    wait_for_subscription_confirm: bool = True
    """Set this to false if you dont want to wait for a subscription confirm."""

    wait_for_subscription_confirm_timeout: int = 30
    """Max time in seconds to wait for a subscription confirmation.
    Only used if ``wait_for_subscription_confirm`` is set to True"""

    _port: int = 80
    _host: str = '0.0.0.0'

    __callbacks = {}
    # __urls = {}

    __active_webhooks = {}

    __authenticate: bool = False

    __hook_thread: Union['threading.Thread', None] = None
    __hook_loop: Union['asyncio.AbstractEventLoop', None] = None
    __hook_runner: Union['web.AppRunner', None] = None

    def __init__(self, callback_url: str, api_client_id: str, port: int):
        self.callback_url = callback_url
        self.__client_id = api_client_id
        self._port = port

    def authenticate(self, auth_token: str) -> None:
        """Set authentication for the Webhook. Can be either a app or user token.

        :param auth_token: str
        :rtype: None
        :raises: Exception
        """
        self.__authenticate = True
        self.__auth_token = auth_token
        if not self.callback_url.startswith('https'):
            raise Exception('HTTPS is required for authenticated webhook.\n'
                            + 'Either use non authenticated webhook or use a HTTPS proxy!')

    def __build_runner(self):
        hook_app = web.Application()
        hook_app.add_routes([web.get('/users/follows', self.__handle_challenge),
                             web.post('/users/follows', self.__handle_user_follows),
                             web.get('/users/changed', self.__handle_challenge),
                             web.post('/users/changed', self.__handle_user_changed),
                             web.get('/streams', self.__handle_challenge),
                             web.post('/streams', self.__handle_stream_changed),
                             web.get('/extensions/transactions', self.__handle_challenge),
                             web.post('/extensions/transactions', self.__handle_extension_transaction_created),
                             web.get('/moderation/moderators/events', self.__handle_challenge),
                             web.post('/moderation/moderators/events', self.__handle_moderator_change_events),
                             web.get('/moderation/banned/events', self.__handle_challenge),
                             web.post('/moderation/banned/events', self.__handle_channel_ban_change_events),
                             web.get('/hypetrain/events', self.__handle_challenge),
                             web.post('/hypetrain/events', self.__handle_hypetrain_events),
                             web.get('/subscriptions/events', self.__handle_challenge),
                             web.post('/subscriptions/events', self.__handle_subscription_events)])
        hook_runner = web.AppRunner(hook_app)
        return hook_runner

    def __run_hook(self, runner: 'web.AppRunner'):
        self.__hook_runner = runner
        self.__hook_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__hook_loop)
        self.__hook_loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, str(self._host), self._port)
        self.__hook_loop.run_until_complete(site.start())
        print('started twitch API hook on port ' + str(self._port))
        self.__hook_loop.run_forever()

    def start(self):
        """Starts the Webhook

        :rtype: None
        """
        self.__hook_thread = threading.Thread(target=self.__run_hook, args=(self.__build_runner(),))
        self.__hook_thread.start()

    def stop(self):
        """Stops the Webhook

        Please make sure to unsubscribe from all subscriptions!

        :rtype: None
        """
        if self.__hook_runner is not None:
            self.__hook_loop.call_soon_threadsafe(self.__hook_loop.stop)
            self.__hook_runner = None
            self.__hook_thread.join()

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    def __build_request_header(self):
        headers = {
            "Client-ID": self.__client_id
        }
        if self.__authenticate:
            headers['Authorization'] = "Bearer " + self.__auth_token
        return headers

    def __api_post_request(self, url: str, data: Union[dict, None] = None):
        headers = self.__build_request_header()
        if data is None:
            return requests.post(url, headers=headers)
        else:
            return requests.post(url, headers=headers, data=data)

    def __api_get_request(self, url: str):
        headers = self.__build_request_header()
        return requests.get(url, headers=headers)

    def __add_callable(self, uuid: UUID, callback_func: Union[Callable, None]) -> None:
        arr = self.__callbacks.get(uuid)
        if arr is None:
            arr = []
        if callback_func is not None:
            arr.append(callback_func)
        self.__callbacks[uuid] = arr

    def _subscribe(self, callback_path: str, topic_url: str, mode: str = "subscribe", callback_full=True):
        """"Subscribe to Twitch Topic"""
        data = {'hub.callback': self.callback_url + callback_path,
                'hub.mode': mode,
                'hub.topic': topic_url,
                'hub.lease_seconds': self.subscribe_least_seconds}
        if not callback_full:
            data['hub.callback'] = callback_path
        if self.secret is not None:
            data['hub.secret'] = self.secret
        result = self.__api_post_request(TWITCH_API_BASE_URL + "webhooks/hub", data=data)
        if result.status_code != 202:
            logging.error(f'Subscription failed! status code: {result.status_code}, body: {result.text}')
        return result.status_code == 202

    def _generic_subscribe(self, callback_path: str, url: str, uuid: UUID, callback_func) -> bool:
        success = self._subscribe(callback_path+"?uuid=" + str(uuid), url)
        if success:
            self.__add_callable(uuid, callback_func)
            # self.__urls[uuid] = url
            self.__active_webhooks[uuid] = {
                'url': url,
                'callback': callback_func,
                'callback_path': callback_path + "?uuid=" + str(uuid),
                'confirmed_subscribe': False,
                'confirmed_unsubscribe': False,
                'active': False
            }
            if self.wait_for_subscription_confirm:
                timeout = time.time() + self.wait_for_subscription_confirm_timeout
                while timeout > time.time() and not self.__active_webhooks.get(uuid)['confirmed_subscribe']:
                    time.sleep(0.1)
                return self.__active_webhooks.get(uuid)['confirmed_subscribe']
        return success

    def _generic_unsubscribe(self, callback_path: str, url: str, callback_full: bool = True) -> bool:
        return self._subscribe(callback_path, url, mode="unsubscribe", callback_full=callback_full)

    def _generic_handle_callback(self, request: 'web.Request', data: Union[dict, list, None]) -> 'web.Response':
        uuid_str = request.rel_url.query.get('uuid')
        if data is None or uuid_str is None:
            return web.Response(text="")
        uuid = UUID(uuid_str)
        callbacks = self.__callbacks.get(uuid)
        if callbacks is None:
            return web.Response(text="")
        for cf in callbacks:
            cf(uuid, data)
        return web.Response(text="")
    # ==================================================================================================================
    # SUBSCRIPTION HELPER
    # ==================================================================================================================

    def unsubscribe_all(self,
                        twitch: 'twitchAPI.twitch.Twitch') -> None:
        """Unsubscribe from all active Webhooks

        :param twitch: App authorized instance of twitchAPI.twitch.Twitch
        :rtype: None
        """
        from pprint import pprint
        data = twitch.get_webhook_subscriptions()
        for d in data.get('data', []):
            pprint(self._generic_unsubscribe(d.get('callback'), d.get('topic'), callback_full=False))

    def renew_subscription(self,
                           uuid: UUID) -> bool:
        """Renew existing topic subscription

        :param uuid: UUID of the subscription to renew
        :rtype: bool
        :returns: True if renewal worked. Note that you still need to wait for the handshake to make sure its renewed.
        """
        url = self.__active_webhooks.get(uuid)
        if url is None:
            raise Exception(f'no subscription found for UUID {str(uuid)}')
        from pprint import pprint
        pprint(url)

    def unsubscribe(self,
                    uuid: UUID) -> bool:
        url = self.__active_webhooks.get(uuid)
        if url is None:
            raise Exception(f'no subscription found for UUID {str(uuid)}')
        success = self._generic_unsubscribe(url.get('callback_path'), url.get('url'))
        if success:
            self.__callbacks.pop(uuid, None)
            if self.wait_for_subscription_confirm:
                timeout = time.time() + self.wait_for_subscription_confirm_timeout
                while timeout > time.time() and not self.__active_webhooks.get(uuid)['confirmed_unsubscribe']:
                    time.sleep(0.1)
                if self.__active_webhooks.get(uuid)['confirmed_unsubscribe']:
                    self.__active_webhooks.pop(uuid)
                else:
                    # unsubscribe failed!
                    return False


        return success

    # ==================================================================================================================
    # SUBSCRIPTIONS
    # ==================================================================================================================

    def subscribe_user_follow(self,
                              from_id: Union[str, None],
                              to_id: Union[str, None],
                              callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to user follow topic.

        Set only from_id if you want to know if User with that id follows someone.\n
        Set only to_id if you want to know if someone follows User with that id.\n
        Set both if you only want to know if from_id follows to_id.\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-user-follows for documentation

        :param from_id: str or None
        :param to_id: str or None
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        param_dict = {"first": 1,
                      "from_id": from_id,
                      "to_id": to_id}
        url = build_url(TWITCH_API_BASE_URL + "users/follows", param_dict, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/users/follows', url, uuid, callback_func), uuid

    def subscribe_stream_changed(self,
                                 user_id: str,
                                 callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to stream changed topic\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-stream-changed for documentation

        :param user_id: str
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        param_dict = {"user_id": user_id}
        url = build_url(TWITCH_API_BASE_URL + "streams", param_dict)
        uuid = get_uuid()
        return self._generic_subscribe('/streams', url, uuid, callback_func), uuid

    def subscribe_user_changed(self,
                               user_id: str,
                               callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to subscription event topic\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-user-changed for documentation

        :param user_id: str
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        param_dict = {"id": user_id}
        url = build_url(TWITCH_API_BASE_URL + "users", param_dict)
        uuid = get_uuid()
        return self._generic_subscribe('/users/changed', url, uuid, callback_func), uuid

    def subscribe_extension_transaction_created(self,
                                                extension_id: str,
                                                callback_func: Union[Callable[[UUID, dict], None], None]) \
            -> Tuple[bool, UUID]:
        """Subscribe to Extension transaction topic\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-extension-transaction-created for documentation

        :param extension_id: str
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        if not self.__authenticate:
            # this requires authentication!
            raise Exception('This subscription requires authentication!')
        params = {
            'extension_id': extension_id,
            'first': 1
        }
        url = build_url(TWITCH_API_BASE_URL + 'extensions/transactions', params)
        uuid = get_uuid()
        return self._generic_subscribe('/extensions/transactions', url, uuid, callback_func), uuid

    def subscribe_moderator_change_events(self,
                                          broadcaster_id: str,
                                          user_id: Union[str, None],
                                          callback_func: Union[Callable[[UUID, dict], None]]) -> Tuple[bool, UUID]:
        """Subscribe to Moderator Change Events topic\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-moderator-change-events for documentation

        :param broadcaster_id: str
        :param user_id: str or None
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/moderators/events', params, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/moderation/moderators/events', url, uuid, callback_func), uuid

    def subscribe_channel_ban_change_events(self,
                                            broadcaster_id: str,
                                            user_id: Union[str, None],
                                            callback_func: Union[Callable[[UUID, dict], None]]) -> Tuple[bool, UUID]:
        """Subscribe to Channel Ban Change Events\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-channel-ban-change-events for documentation

        :param broadcaster_id: str
        :param user_id: str or None
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/banned/events', params, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/moderation/banned/events', url, uuid, callback_func), uuid

    def subscribe_subscription_events(self,
                                      broadcaster_id: str,
                                      callback_func: Union[Callable[[UUID, dict], None]],
                                      user_id: Union[str, None] = None,
                                      gifter_id: Union[str, None] = None,
                                      gifter_name: Union[str, None] = None) -> Tuple[bool, UUID]:
        """Subscribe to Subscription Events Topic\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-subscription-events for documentation

        :param broadcaster_id: str
        :param callback_func: function for callback
        :param user_id: optional str
        :param gifter_id: optional str
        :param gifter_name: optional str
        :rtype: bool, UUID
        """
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1,
            'gifter_id': gifter_id,
            'gifter_name': gifter_name,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'subscriptions/events', params, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/subscriptions/events', url, uuid, callback_func), uuid

    def subscribe_hype_train_events(self,
                                    broadcaster_id: str,
                                    callback_func: Union[Callable[[UUID, dict], None]]) -> Tuple[bool, UUID]:
        """Subscribe to Hype Train Events\n
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-hype-train-event for documentation

        :param broadcaster_id: str
        :param callback_func: function for callback
        :rtype: bool, UUID
        """
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1
        }
        url = build_url(TWITCH_API_BASE_URL + 'hypetrain/events', params)
        uuid = get_uuid()
        return self._generic_subscribe('/hypetrain/events', url, uuid, callback_func), uuid

    # ==================================================================================================================
    # HANDLERS
    # ==================================================================================================================

    async def __handle_default(self, request: 'web.Request'):
        return web.Response(text="pyTwitchAPI webhook")

    async def __handle_stream_changed(self, request: 'web.Request'):
        d = await get_json(request)
        data = None
        if d is not None:
            if len(d['data']) > 0:
                data = d['data'][0]
                data = make_fields_datetime(data, ['started_at'])
            else:
                data = {
                    'type': 'offline'
                }
        return self._generic_handle_callback(request, data)

    async def __handle_user_follows(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, ['followed_at'])
        return self._generic_handle_callback(request, data)

    async def __handle_user_changed(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
        return self._generic_handle_callback(request, data)

    async def __handle_extension_transaction_created(self, request: 'web.Request'):
        d = await get_json(request)
        data = d
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, ['timestamp'])
        return self._generic_handle_callback(request, data)

    async def __handle_challenge(self, request: 'web.Request'):
        challenge = request.rel_url.query.get('hub.challenge')
        from pprint import pprint
        print('in challenge:')
        pprint(request.rel_url.query.items())
        if challenge is not None:
            # found challenge, lets answer it
            if request.rel_url.query.get('hub.mode') == 'subscribe':
                # we treat this as active as soon as we answer the challenge
                self.__active_webhooks.get(UUID(request.rel_url.query.get('uuid')))['active'] = True
                self.__active_webhooks.get(UUID(request.rel_url.query.get('uuid')))['confirmed_subscribe'] = True
            if request.rel_url.query.get('hub.mode') == 'unsubscribe':
                if UUID(request.rel_url.query.get('uuid')) in self.__active_webhooks.keys():
                    # we treat this as invalid as soon as we answer the challenge
                    if self.wait_for_subscription_confirm:
                        self.__active_webhooks.get(UUID(request.rel_url.query.get('uuid')))['confirmed_unsubscribe'] = True
                    else:
                        self.__active_webhooks.pop(UUID(request.rel_url.query.get('uuid')))
            return web.Response(text=challenge)
        return web.Response(status=500)

    async def __handle_moderator_change_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, ['event_timestamp'])
            return self._generic_handle_callback(request, data)

    async def __handle_channel_ban_change_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, ['event_timestamp'])
        return self._generic_handle_callback(request, data)

    async def __handle_subscription_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, 'event_timestamp')
        return self._generic_handle_callback(request, data)

    async def __handle_hypetrain_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data = make_fields_datetime(data, ['event_timestamp',
                                               'cooldown_end_time',
                                               'expires_at',
                                               'started_at'])
            data = fields_to_enum(data, ['type'], HypeTrainContributionMethod, HypeTrainContributionMethod.UNKNOWN)
        return self._generic_handle_callback(request, data)
