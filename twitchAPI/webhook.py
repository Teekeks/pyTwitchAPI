#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Full Implementation of the Twitch Webhook
-----------------------------------------

.. warning:: Webhooks have been discontinued.

The Webhook runs in its own thread, calling the given callback function whenever an webhook event happens.

Look at the `Twitch Webhook reference <https://dev.twitch.tv/docs/api/webhooks-reference>`__ to find the topics you are
interested in.

************
Requirements
************

You need to have a public IP with a port open. That port will be 80 by default.
Authentication is off by default but you can choose to authenticate to use some Webhook Topics or to get more information.

.. note:: Please note that Your Endpoint URL has to be HTTPS if you need authentication which means that you probably
            need a reverse proxy like nginx. You can also hand in a valid ssl context to be used in the constructor.

You can check on whether or not your webhook is publicly reachable by navigating to the URL set in `callback_url`.
You should get a 200 response with the text `pyTwitchAPI webhook`.


*******************
Short code example:
*******************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.webhook import TwitchWebHook
    from pprint import pprint

    def callback_stream_changed(uuid, data):
        print('Callback for UUID ' + str(uuid))
        pprint(data)

    twitch = Twitch(td['app_id'], td['secret'])
    twitch.authenticate_app([])

    user_info = twitch.get_users(logins=['my_twitch_user'])
    user_id = user_info['data'][0]['id']
    # basic setup
    # Please note that the first parameter is the domain your webhook is reachable from the outside, the last parameter
    # is the port that the Webhook should use
    hook = TwitchWebHook("https://my.cool.domain.net:443", 'my_app_id', 8080)
    hook.authenticate(twitch)
    hook.start()
    print('subscribing to hook:')
    success, uuid = hook.subscribe_stream_changed(user_id, callback_stream_changed)
    pprint(success)
    pprint(twitch.get_webhook_subscriptions())
    # the webhook is now running and you are subscribed to the topic you want to listen to. lets idle a bit...
    input('press Enter to shut down')
    hook.stop()
    print('done')

*********************
Subscription handling
*********************

You can subscribe to webhook topics using the :code:`subscribe_` prefixed methods.

If :attr:`~.TwitchWebHook.wait_for_subscription_confirm` is True (default), this will wait for the full handshake and
confirmation to happen, otherwise the returned success value  might be inaccurate in case the subscription itself
succeeded but the final handshake failed.

You can unsubscribe from a webhook subscription at any time by using :meth:`~twitchAPI.webhook.TwitchWebHook.unsubscribe`

If :attr:`~.TwitchWebHook.unsubscribe_on_stop` is True (default), you don't need to manually unsubscribe from topics.

By default, subscriptions will be automatically renewed one minute before they run out for as long as the
webhook is running.

You can also use :meth:`~twitchAPI.webhook.TwitchWebHook.unsubscribe_all` to unsubscribe from all topic subscriptions at
once. This will also unsubscribe from topics that where left over from a previous run.

***********************
Fixing typical problems
***********************

* Make sure that your set URL is reachable from outside your network.
* Make sure that you use a non self signed SSL certificate (use one from e.g. Let's Encrypt) if you use any Authentication.
* If you change your domain's DNS, it can take up to 24 hours (or more) to propagate the changes across the entire internet and reach the Twitch servers.

********************
Class Documentation:
********************
"""


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


class TwitchWebHook:
    """Webhook integration for the Twitch Helix API.

    :param str callback_url: The full URL of the webhook.
    :param str api_client_id: The id of your API client
    :param int port: the port on which this webhook should run
    :param ~ssl.SSLContext ssl_context: optional ssl context to be used |default| :code:`None`
    :var str secret: A random secret string. Set this for added security.
    :var str callback_url: The full URL of the webhook.
    :var int subscribe_least_seconds: The duration in seconds for how long you want to subscribe to webhhoks.
                    Min 300 Seconds, Max 864000 Seconds. |default| :code:`600`
    :var bool auto_renew_subscription: If True, automatically renew all webhooks once they get close to running out.
                    **Only disable this if you know what you are doing.** |default| :code:`True`
    :var bool wait_for_subscription_confirm: Set this to false if you dont want to wait for a subscription confirm.
                    |default| :code:`True`
    :var int wait_for_subscription_confirm_timeout: Max time in seconds to wait for a subscription confirmation.
                    Only used if ``wait_for_subscription_confirm`` is set to True. |default| :code:`30`
    :var bool unsubscribe_on_stop: Unsubscribe all currently active Webhooks on calling `stop()`
                    |default| :code:`True`
    """

    secret = None
    callback_url = None
    subscribe_least_seconds: int = 600
    auto_renew_subscription: bool = True
    wait_for_subscription_confirm: bool = True
    wait_for_subscription_confirm_timeout: int = 30
    unsubscribe_on_stop: bool = True
    _port: int = 80
    _host: str = '0.0.0.0'
    __twitch: Twitch = None
    __task_refresh = None
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
        raise DeprecatedError()  # Webhooks are deprecated and can no longer be used

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
                             web.post('/subscriptions/events', self.__handle_subscription_events),
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
        self.__logger.info('started twitch API hook on port ' + str(self._port))
        # add refresh task
        if self.auto_renew_subscription:
            self.__task_refresh = self.__hook_loop.create_task(self.__refresh_task())
        try:
            self.__hook_loop.run_forever()
        except (CancelledError, asyncio.CancelledError):
            pass

    async def __refresh_task(self):
        while True:
            # renew 1 Min before timer runs out:
            await asyncio.sleep(self.subscribe_least_seconds - 60)
            # make sure that the auth token is still valid:
            if self.__authenticate:
                self.__twitch.refresh_used_token()
            for key in self.__active_webhooks.keys():
                self.renew_subscription(key)

    def start(self):
        """Starts the Webhook

        :rtype: None
        :raises ValueError: if subscribe_least_seconds is not in range 300 to 864000
        :raises RuntimeError: if webhook is already running
        """
        if self.subscribe_least_seconds < 60 * 5 or self.subscribe_least_seconds > 864000:
            # at least 5 min, max 864000 seconds
            raise ValueError('subscribe_least_second has to be in range 300 to 864000')
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
                for uuid in all_keys:
                    self.unsubscribe(uuid)
            if self.auto_renew_subscription:
                self.__task_refresh.cancel()
            self.__hook_loop.call_soon_threadsafe(self.__hook_loop.stop)
            self.__hook_runner = None
            self.__hook_thread.join()
            self.__running = False

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    def __build_request_header(self):
        headers = {
            "Client-ID": self.__client_id
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
        self.__logger.debug(f'{mode} to topic {topic_url} for {callback_path}')
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
            self.__logger.error(f'Subscription failed! status code: {result.status_code}, body: {result.text}')
        return result.status_code == 202

    def _generic_subscribe(self,
                           callback_path: str,
                           url: str,
                           uuid: UUID,
                           callback_func,
                           auth_type: AuthType,
                           auth_scope: List[AuthScope]) -> bool:
        if auth_type != AuthType.NONE and not self.__twitch.has_required_auth(auth_type, auth_scope):
            raise UnauthorizedException('required authentication not set or missing auth scope')
        success = self._subscribe(callback_path+"?uuid=" + str(uuid), url)
        if success:
            self.__add_callable(uuid, callback_func)
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
        self.__logger.debug(f'handle callback for uuid {uuid_str}')
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

    __unsubscribe_all_helper = {}

    def unsubscribe_all(self,
                        twitch: Twitch) -> bool:
        """Unsubscribe from all Webhooks that use the callback URL set in `callback_url`\n
        **If `wait_for_subscription_confirm` is False, the response might be
        True even tho the unsubscribe action failed.**

        :param ~twitchAPI.twitch.Twitch twitch: App authorized instance of :class:`~twitchAPI.twitch.Twitch`
        :rtype: bool
        :returns: True if all webhooks could be unsubscribed, otherwise False.
        """
        self.__unsubscribe_all_helper = {}
        data = twitch.get_webhook_subscriptions()
        sub_responses = []
        for d in data.get('data', []):
            uuid = extract_uuid_str_from_url(d.get('callback'))
            if uuid is not None and d.get('callback').startswith(self.callback_url):
                self.__unsubscribe_all_helper[uuid] = False
                sub_responses.append(self._generic_unsubscribe(d.get('callback'), d.get('topic'), callback_full=False))
        if self.wait_for_subscription_confirm:
            timeout = time.time() + self.wait_for_subscription_confirm_timeout
            while timeout > time.time() and not all(self.__unsubscribe_all_helper.values()):
                time.sleep(0.1)
            return all(self.__unsubscribe_all_helper.values()) and all(sub_responses)
        else:
            return all(sub_responses)

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
        self.__logger.info('renewing webhook ' + str(uuid))
        return self._subscribe(url.get('callback_path'), url.get('url'))

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
                    time.sleep(0.05)
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
        :raises ValueError: if both from_id and to_id are None
        :rtype: bool, UUID
        """
        if from_id is None and to_id is None:
            raise ValueError('specify at least one of from_id and to_id')
        param_dict = {"first": 1,
                      "from_id": from_id,
                      "to_id": to_id}
        url = build_url(TWITCH_API_BASE_URL + "users/follows", param_dict, remove_none=True)
        uuid = get_uuid()
        return self._generic_subscribe('/users/follows', url, uuid, callback_func, AuthType.NONE, []), uuid

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
        return self._generic_subscribe('/streams', url, uuid, callback_func, AuthType.NONE, []), uuid

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
        return self._generic_subscribe('/users/changed', url, uuid, callback_func, AuthType.USER, []), uuid

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
        return self._generic_subscribe('/extensions/transactions', url, uuid, callback_func, AuthType.APP, []), uuid

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
        return self._generic_subscribe('/moderation/moderators/events',
                                       url,
                                       uuid,
                                       callback_func,
                                       AuthType.USER,
                                       []), uuid

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
        return self._generic_subscribe('/moderation/banned/events', url, uuid, callback_func, AuthType.USER, []), uuid

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
        return self._generic_subscribe('/subscriptions/events',
                                       url,
                                       uuid,
                                       callback_func,
                                       AuthType.USER,
                                       [AuthScope.CHANNEL_READ_SUBSCRIPTIONS]), uuid

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
        return self._generic_subscribe('/hypetrain/events',
                                       url,
                                       uuid,
                                       callback_func,
                                       AuthType.USER,
                                       [AuthScope.CHANNEL_READ_HYPE_TRAIN]), uuid

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
        if challenge is not None:
            self.__logger.debug(f'received challenge for {request.rel_url.query.get("uuid")}')
            # found challenge, lets answer it
            if request.rel_url.query.get('hub.mode') == 'subscribe':
                # we treat this as active as soon as we answer the challenge
                self.__active_webhooks.get(UUID(request.rel_url.query.get('uuid')))['active'] = True
                self.__active_webhooks.get(UUID(request.rel_url.query.get('uuid')))['confirmed_subscribe'] = True
            if request.rel_url.query.get('hub.mode') == 'unsubscribe':
                uuid_str = request.rel_url.query.get('uuid')
                if uuid_str in self.__unsubscribe_all_helper.keys():
                    self.__unsubscribe_all_helper[uuid_str] = True
                if UUID(uuid_str) in self.__active_webhooks.keys():
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
            data = make_fields_datetime(data, ['event_timestamp'])
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
