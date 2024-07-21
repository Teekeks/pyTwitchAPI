#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
EventSub Webhook
----------------

.. note:: EventSub Webhook is targeted at programs which have to subscribe to topics for multiple broadcasters.\n
    Should you only need to target a single broadcaster or are building a client side project, look at :doc:`/modules/twitchAPI.eventsub.websocket`

EventSub lets you listen for events that happen on Twitch.

The EventSub client runs in its own thread, calling the given callback function whenever an event happens.

************
Requirements
************

.. note:: Please note that Your Endpoint URL has to be HTTPS, has to run on Port 443 and requires a valid, non self signed certificate
            This most likely means, that you need a reverse proxy like nginx. You can also hand in a valid ssl context to be used in the constructor.

In the case that you don't hand in a valid ssl context to the constructor, you can specify any port you want in the constructor and handle the
bridge between this program and your public URL on port 443 via reverse proxy.\n
You can check on whether or not your webhook is publicly reachable by navigating to the URL set in `callback_url`.
You should get a 200 response with the text :code:`pyTwitchAPI eventsub`.

*******************
Listening to topics
*******************

After you started your EventSub client, you can use the :code:`listen_` prefixed functions to listen to the topics you are interested in.

Look at :ref:`eventsub-available-topics` to find the topics you are interested in.

The function you hand in as callback will be called whenever that event happens with the event data as a parameter,
the type of that parameter is also listed in the link above.

************
Code Example
************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.eventsub.webhook import EventSubWebhook
    from twitchAPI.object.eventsub import ChannelFollowEvent
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope
    import asyncio

    TARGET_USERNAME = 'target_username_here'
    EVENTSUB_URL = 'https://url.to.your.webhook.com'
    APP_ID = 'your_app_id'
    APP_SECRET = 'your_app_secret'
    TARGET_SCOPES = [AuthScope.MODERATOR_READ_FOLLOWERS]


    async def on_follow(data: ChannelFollowEvent):
        # our event happened, lets do things with the data we got!
        print(f'{data.event.user_name} now follows {data.event.broadcaster_user_name}!')


    async def eventsub_webhook_example():
        # create the api instance and get the ID of the target user
        twitch = await Twitch(APP_ID, APP_SECRET)
        user = await first(twitch.get_users(logins=TARGET_USERNAME))

        # the user has to authenticate once using the bot with our intended scope.
        # since we do not need the resulting token after this authentication, we just discard the result we get from authenticate()
        # Please read up the UserAuthenticator documentation to get a full view of how this process works
        auth = UserAuthenticator(twitch, TARGET_SCOPES)
        await auth.authenticate()

        # basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
        eventsub = EventSubWebhook(EVENTSUB_URL, 8080, twitch)

        # unsubscribe from all old events that might still be there
        # this will ensure we have a clean slate
        await eventsub.unsubscribe_all()
        # start the eventsub client
        eventsub.start()
        # subscribing to the desired eventsub hook for our user
        # the given function (in this example on_follow) will be called every time this event is triggered
        # the broadcaster is a moderator in their own channel by default so specifying both as the same works in this example
        await eventsub.listen_channel_follow_v2(user.id, user.id, on_follow)

        # eventsub will run in its own process
        # so lets just wait for user input before shutting it all down again
        try:
            input('press Enter to shut down...')
        finally:
            # stopping both eventsub as well as gracefully closing the connection to the API
            await eventsub.stop()
            await twitch.close()
        print('done')


    # lets run our example
    asyncio.run(eventsub_webhook_example())"""
import asyncio
import hashlib
import hmac
import threading
from functools import partial
from json import JSONDecodeError
from random import choice
from string import ascii_lowercase
from ssl import SSLContext
from time import sleep
from typing import Optional, Union, Callable, Awaitable
import datetime
from collections import deque

from aiohttp import web, ClientSession

from twitchAPI.eventsub.base import EventSubBase
from ..twitch import Twitch
from ..helper import done_task_callback
from ..type import TwitchBackendException, EventSubSubscriptionConflict, EventSubSubscriptionError, EventSubSubscriptionTimeout, \
    TwitchAuthorizationException

__all__ = ['EventSubWebhook']


class EventSubWebhook(EventSubBase):

    def __init__(self,
                 callback_url: str,
                 port: int,
                 twitch: Twitch,
                 ssl_context: Optional[SSLContext] = None,
                 host_binding: str = '0.0.0.0',
                 subscription_url: Optional[str] = None,
                 callback_loop: Optional[asyncio.AbstractEventLoop] = None,
                 revocation_handler: Optional[Callable[[dict], Awaitable[None]]] = None,
                 message_deduplication_history_length: int = 50):
        """
        :param callback_url: The full URL of the webhook.
        :param port: the port on which this webhook should run
        :param twitch: a app authenticated instance of :const:`~twitchAPI.twitch.Twitch`
        :param ssl_context: optional ssl context to be used |default| :code:`None`
        :param host_binding: the host to bind the internal server to |default| :code:`0.0.0.0`
        :param subscription_url: Alternative subscription URL, useful for development with the twitch-cli
        :param callback_loop: The asyncio eventloop to be used for callbacks. \n
            Set this if you or a library you use cares about which asyncio event loop is running the callbacks.
            Defaults to the one used by EventSub Webhook.
        :param revocation_handler: Optional handler for when subscriptions get revoked. |default| :code:`None`
        :param message_deduplication_history_length: The amount of messages being considered for the duplicate message deduplication. |default| :code:`50`
        """
        super().__init__(twitch, 'twitchAPI.eventsub.webhook')
        self.callback_url: str = callback_url
        """The full URL of the webhook."""
        if self.callback_url[-1] == '/':
            self.callback_url = self.callback_url[:-1]
        self.secret: str = ''.join(choice(ascii_lowercase) for _ in range(20))
        """A random secret string. Set this for added security. |default| :code:`A random 20 character long string`"""
        self.wait_for_subscription_confirm: bool = True
        """Set this to false if you don't want to wait for a subscription confirm. |default| :code:`True`"""
        self.wait_for_subscription_confirm_timeout: int = 30
        """Max time in seconds to wait for a subscription confirmation. Only used if ``wait_for_subscription_confirm`` is set to True. 
            |default| :code:`30`"""

        self._port: int = port
        self.subscription_url: Optional[str] = subscription_url
        """Alternative subscription URL, useful for development with the twitch-cli"""
        if self.subscription_url is not None and self.subscription_url[-1] != '/':
            self.subscription_url += '/'
        self._callback_loop = callback_loop
        self._host: str = host_binding
        self.__running = False
        self.revokation_handler: Optional[Callable[[dict], Awaitable[None]]] = revocation_handler
        """Optional handler for when subscriptions get revoked."""
        self._startup_complete = False
        self.unsubscribe_on_stop: bool = True
        """Unsubscribe all currently active Webhooks on calling :const:`~twitchAPI.eventsub.EventSub.stop()` |default| :code:`True`"""

        self._closing = False
        self.__ssl_context: Optional[SSLContext] = ssl_context
        self.__active_webhooks = {}
        self.__hook_thread: Union['threading.Thread', None] = None
        self.__hook_loop: Union['asyncio.AbstractEventLoop', None] = None
        self.__hook_runner: Union['web.AppRunner', None] = None
        self._task_callback = partial(done_task_callback, self.logger)
        if not self.callback_url.startswith('https'):
            raise RuntimeError('HTTPS is required for authenticated webhook.\n'
                               + 'Either use non authenticated webhook or use a HTTPS proxy!')
        self._msg_id_history: deque = deque(maxlen=message_deduplication_history_length)

    async def _unsubscribe_hook(self, topic_id: str) -> bool:
        return True

    def __build_runner(self):
        hook_app = web.Application()
        hook_app.add_routes([web.post('/callback', self.__handle_callback),
                             web.get('/', self.__handle_default)])
        return web.AppRunner(hook_app)

    def __run_hook(self, runner: 'web.AppRunner'):
        self.__hook_runner = runner
        self.__hook_loop = asyncio.new_event_loop()
        if self._callback_loop is None:
            self._callback_loop = self.__hook_loop
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
        :raises RuntimeError: if EventSub is not running
        """
        if not self.__running:
            raise RuntimeError('EventSubWebhook is not running')
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

    async def _build_request_header(self):
        token = await self._twitch.get_refreshed_app_token()
        if token is None:
            raise TwitchAuthorizationException('no Authorization set!')
        return {
            'Client-ID': self._twitch.app_id,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    async def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback, event, is_batching_enabled: Optional[bool] = None) -> str:
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
        if is_batching_enabled is not None:
            data['is_batching_enabled'] = is_batching_enabled

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
        self._add_callback(sub_id, callback, event)
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

    async def _handle_revokation(self, data):
        sub_id: str = data.get('subscription', {}).get('id')
        self.logger.debug(f'got revocation of subscription {sub_id} for reason {data.get("subscription").get("status")}')
        if sub_id not in self._callbacks.keys():
            self.logger.warning(f'unknown subscription {sub_id} got revoked. ignore')
            return
        self._callbacks.pop(sub_id)
        if self.revokation_handler is not None:
            t = self._callback_loop.create_task(self.revokation_handler(data))
            t.add_done_callback(self._task_callback)

    async def __handle_callback(self, request: 'web.Request'):
        try:
            data: dict = await request.json()
        except JSONDecodeError:
            self.logger.error('got request with malformed body! Discarding message')
            return web.Response(status=400)
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
            msg_type = request.headers['Twitch-Eventsub-Message-Type']
            if msg_type.lower() == 'revocation':
                await self._handle_revokation(data)
            else:
                msg_id = request.headers.get('Twitch-Eventsub-Message-Id')
                if msg_id is not None and msg_id in self._msg_id_history:
                    self.logger.warning(f'got message with duplicate id {msg_id}! Discarding message')
                else:
                    self._msg_id_history.append(msg_id)
                    dat = callback['event'](**data)
                    t = self._callback_loop.create_task(callback['callback'](dat))
                    t.add_done_callback(self._task_callback)
        return web.Response(status=200)
