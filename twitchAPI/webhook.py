#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
from typing import Union, Tuple, Callable
from .helper import build_url, TWITCH_API_BASE_URL, get_uuid, get_json
import requests
from aiohttp import web
import threading
import asyncio
from uuid import UUID
from datetime import datetime
import logging
from dateutil import parser as du_parser


class TwitchWebHook:

    secret = None
    __client_id = None
    __auth_token = None
    callback_url = None
    subscribe_least_seconds: int = 864000
    _port: int = 80
    _host: str = '0.0.0.0'

    __callbacks = {}
    __urls = {}

    __authenticate: bool = False

    __hook_thread: Union['threading.Thread', None] = None
    __hook_loop: Union['asyncio.AbstractEventLoop', None] = None
    __hook_runner: Union['web.AppRunner', None] = None

    def __init__(self, callback_url: str, api_client_id: str, port: int):
        self.callback_url = callback_url
        self.__client_id = api_client_id
        self._port = port

    def authenticate(self, auth_token: str) -> None:
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
        self.__hook_thread = threading.Thread(target=self.__run_hook, args=(self.__build_runner(),))
        self.__hook_thread.start()

    def stop(self):
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

    def _subscribe(self, callback_path: str, topic_url: str, mode: str = "subscribe"):
        """"Subscribe to Twitch Topic"""
        data = {'hub.callback': self.callback_url + callback_path,
                'hub.mode': mode,
                'hub.topic': topic_url,
                'hub.lease_seconds': self.subscribe_least_seconds}
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
            self.__urls[uuid] = url
        return success

    def _generic_unsubscribe(self, callback_path: str, uuid: UUID) -> bool:
        url = self.__urls.get(uuid)
        if url is None:
            raise Exception(f'no subscription found for UUID {str(uuid)}')
        success = self._subscribe(callback_path + "?uuid=" + str(uuid), url, mode="unsubscribe")
        if success:
            self.__urls.pop(uuid, None)
            self.__callbacks.pop(uuid, None)
        return success

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
    # SUBSCRIPTIONS
    # ==================================================================================================================

    def subscribe_user_follow(self,
                              from_id: Union[str, None],
                              to_id: Union[str, None],
                              callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to user follow topic
        Set only from_id if you want to know if User with that id follows someone.
        Set only to_id if you want to know if someone follows User with that id.
        Set both if you only want to know if from_id follows to_id.
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-user-follows for documentation"""
        param_dict = {"first": 1,
                      "from_id": from_id,
                      "to_id": to_id}
        url = build_url(TWITCH_API_BASE_URL + "users/follows", param_dict, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/users/follows', url, uuid, callback_func), uuid

    def unsubscribe_user_follow(self, uuid: UUID) -> bool:
        """Unsubscribe to user follow topic"""
        return self._generic_unsubscribe('/users/follows', uuid)

    def subscribe_stream_changed(self,
                                 user_id: str,
                                 callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to stream changed topic
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-stream-changed for documentation"""
        param_dict = {"user_id": user_id}
        url = build_url(TWITCH_API_BASE_URL + "streams", param_dict)
        uuid = get_uuid()
        return self._generic_subscribe('/streams', url, uuid, callback_func), uuid

    def unsubscribe_stream_changed(self, uuid: UUID) -> bool:
        """Unsubscribe to stream changed topic"""
        return self._generic_unsubscribe('/streams', uuid)

    def subscribe_user_changed(self,
                               user_id: str,
                               callback_func: Union[Callable[[UUID, dict], None], None]) -> Tuple[bool, UUID]:
        """Subscribe to subscription event topic
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-user-changed for documentation"""
        param_dict = {"id": user_id}
        url = build_url(TWITCH_API_BASE_URL + "users", param_dict)
        uuid = get_uuid()
        return self._generic_subscribe('/users/changed', url, uuid, callback_func), uuid

    def unsubscribe_user_changed(self, uuid: UUID) -> bool:
        """Unsubscribe from subscription event topic"""
        return self._generic_unsubscribe("/users/changed", uuid)

    def subscribe_extension_transaction_created(self,
                                                extension_id: str,
                                                callback_func: Union[Callable[[UUID, dict], None], None]) \
            -> Tuple[bool, UUID]:
        """Subscribe to Extension transaction topic
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-extension-transaction-created for documentation"""
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

    def unsubscribe_extension_transactions_created(self, uuid: UUID) -> bool:
        """Unsubscribe from Extension transaction created Topic"""
        return self._generic_unsubscribe('/extensions/transactions', uuid)

    def subscribe_moderator_change_events(self,
                                          broadcaster_id: str,
                                          user_id: Union[str, None],
                                          callback_func: Union[Callable[[UUID, dict], None]]) -> Tuple[bool, UUID]:
        """Subscribe to Moderator Change Events Topic
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-moderator-change-events for documentation"""
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/moderators/events', params, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/moderation/moderators/events', url, uuid, callback_func), uuid

    def unsubscribe_moderator_change_events(self, uuid: UUID) -> bool:
        """Unsubscribe from Moderator Change Events Topic"""
        return self._generic_unsubscribe('/moderation/moderators/events', uuid)

    def subscribe_channel_ban_change_events(self,
                                            broadcaster_id: str,
                                            user_id: Union[str, None],
                                            callback_func: Union[Callable[[UUID, dict], None]]) -> Tuple[bool, UUID]:
        """Subscribe to Channel Ban Change Events
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-channel-ban-change-events for documentation"""
        params = {
            'broadcaster_id': broadcaster_id,
            'first': 1,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/banned/events', params, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/moderation/banned/events', url, uuid, callback_func), uuid

    def unsubscribe_channel_ban_change_events(self, uuid: UUID) -> bool:
        """Unsubscribe from Channel Ban Change Events Topic"""
        return self._generic_unsubscribe('/moderation/banned/events', uuid)

    def subscribe_subscription_events(self,
                                      broadcaster_id: str,
                                      callback_func: Union[Callable[[UUID, dict], None]],
                                      user_id: Union[str, None] = None,
                                      gifter_id: Union[str, None] = None,
                                      gifter_name: Union[str, None] = None) -> Tuple[bool, UUID]:
        """Subscribe to Subscription Events Topic
        See https://dev.twitch.tv/docs/api/webhooks-reference#topic-subscription-events for documentation"""
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

    def unsubscribe_subscription_events(self, uuid: UUID) -> bool:
        """Unsubscribe from Subscription Events Topic"""
        return self._generic_unsubscribe('/subscriptions/events', uuid)

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
                data['started_at'] = datetime.fromisoformat(data['started_at'])
            else:
                data = {
                    'type': 'offline'
                }
        return self._generic_handle_callback(request, data)

    async def __handle_user_follows(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data['followed_at'] = du_parser.isoparse(data['followed_at'])
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
            data['timestamp'] = du_parser.isoparse(data['timestamp'])
        return self._generic_handle_callback(request, data)

    async def __handle_challenge(self, request: 'web.Request'):
        challenge = request.rel_url.query.get('hub.challenge')
        if challenge is not None:
            # found challenge, lets answer it
            return web.Response(text=challenge)
        return web.Response(status=500)

    async def __handle_moderator_change_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data['event_timestamp'] = du_parser.isoparse(data['event_timestamp'])
            return self._generic_handle_callback(request, data)

    async def __handle_channel_ban_change_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data['event_timestamp'] = du_parser.isoparse(data['event_timestamp'])
        return self._generic_handle_callback(request, data)

    async def __handle_subscription_events(self, request: 'web.Request'):
        data = await get_json(request)
        if data is not None:
            data = data['data'][0]
            data['event_timestamp'] = du_parser.isoparse(data['event_timestamp'])
        return self._generic_handle_callback(request, data)
