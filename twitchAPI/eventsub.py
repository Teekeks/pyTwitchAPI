#  Copyright (c) 2021. Lena "Teekeks" During <info@teawork.de>
"""
EventSub Client
---------------

EventSub lets you listen for events that happen on Twitch.

The EventSub client runs in its own thread, calling the given callback function whenever an event happens.

Look at the `Twitch EventSub reference <https://dev.twitch.tv/docs/eventsub/eventsub-reference>`__ to find the topics
you are interested in.

************
Requirements
************

.. note:: Please note that Your Endpoint URL has to be HTTPS, has to run on Port 443 and requires a valid, non self signed certificate
            This most likely means, that you need a reverse proxy like nginx. You can also hand in a valid ssl context to be used in the constructor.

In the case that you don't hand in a valid ssl context to the constructor, you can specify any port you want in the constructor and handle the
bridge between this program and your public URL on port 443 via reverse proxy.\n
You can check on whether or not your webhook is publicly reachable by navigating to the URL set in `callback_url`.
You should get a 200 response with the text `pyTwitchAPI eventsub`.

*******************
Listening to topics
*******************

After you started your EventSub client, you can use the :code:`listen_` prefixed functions to listen to the topics you are interested in.

The function you hand in as callback will be called whenever that event happens with the event data as a parameter.

************
Code Example
************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.eventsub import EventSub
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.types import AuthScope
    import asyncio

    TARGET_USERNAME = 'target_username_here'
    EVENTSUB_URL = 'https://url.to.your.webhook.com'
    APP_ID = 'your_app_id'
    APP_SECRET = 'your_app_secret'
    TARGET_SCOPES = [AuthScope.MODERATOR_READ_FOLLOWERS]


    async def on_follow(data: dict):
        # our event happend, lets do things with the data we got!
        print(data)


    async def eventsub_example():
        # create the api instance and get the ID of the target user
        twitch = await Twitch(APP_ID, APP_SECRET)
        user = await first(twitch.get_users(logins=TARGET_USERNAME))

        # the user has to authenticate once using the bot with our intended scope.
        # since we do not need the resulting token after this authentication, we just discard the result we get from authenticate()
        # Please read up the UserAuthenticator documentation to get a full view of how this process works
        auth = UserAuthenticator(twitch, TARGET_SCOPES)
        await auth.authenticate()

        # basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
        event_sub = EventSub(EVENTSUB_URL, APP_ID, 8080, twitch)

        # unsubscribe from all old events that might still be there
        # this will ensure we have a clean slate
        await event_sub.unsubscribe_all()
        # start the eventsub client
        event_sub.start()
        # subscribing to the desired eventsub hook for our user
        # the given function (in this example on_follow) will be called every time this event is triggered
        # the broadcaster is a moderator in their own channel by default so specifying both as the same works in this example
        await event_sub.listen_channel_follow_v2(user.id, user.id, on_follow)

        # eventsub will run in its own process
        # so lets just wait for user input before shutting it all down again
        try:
            input('press Enter to shut down...')
        finally:
            # stopping both eventsub as well as gracefully closing the connection to the API
            await event_sub.stop()
            await twitch.close()
        print('done')


    # lets run our example
    asyncio.run(eventsub_example())

*******************
Class Documentation
*******************
"""
import datetime
import random
import string
import time

from .helper import TWITCH_API_BASE_URL, remove_none_values
from .types import *
from aiohttp import web, ClientSession
import threading
import asyncio
from logging import getLogger, Logger
from .twitch import Twitch
from ssl import SSLContext
from .types import EventSubSubscriptionTimeout, EventSubSubscriptionConflict, EventSubSubscriptionError
import hmac
import hashlib

from typing import Union, Callable, Optional, Awaitable


__all__ = ['CALLBACK_TYPE', 'EventSub']


CALLBACK_TYPE = Callable[[dict], Awaitable[None]]


class EventSub:
    """EventSub integration for the Twitch Helix API.
    """

    def __init__(self,
                 callback_url: str,
                 api_client_id: str,
                 port: int,
                 twitch: Twitch,
                 ssl_context: Optional[SSLContext] = None):
        """
        :param callback_url: The full URL of the webhook.
        :param api_client_id: The id of your API client
        :param port: the port on which this webhook should run
        :param twitch: a app authenticated instance of :const:`~twitchAPI.twitch.Twitch`
        :param ssl_context: optional ssl context to be used |default| :code:`None`
        """
        self.callback_url: str = callback_url
        """The full URL of the webhook."""
        self.__client_id: str = api_client_id
        self._port: int = port
        self.__ssl_context: Optional[SSLContext] = ssl_context
        self.__twitch: Twitch = twitch
        self.logger: Logger = getLogger('twitchAPI.eventsub')
        """The logger used for EventSub related log messages"""
        self.secret: str = ''.join(random.choice(string.ascii_lowercase) for _ in range(20))
        """A random secret string. Set this for added security. |default| :code:`A random 20 character long string`"""
        self.wait_for_subscription_confirm: bool = True
        """Set this to false if you don't want to wait for a subscription confirm. |default| :code:`True`"""
        self.wait_for_subscription_confirm_timeout: int = 30
        """Max time in seconds to wait for a subscription confirmation. Only used if ``wait_for_subscription_confirm`` is set to True. 
            |default| :code:`30`"""
        self.unsubscribe_on_stop: bool = True
        """Unsubscribe all currently active Webhooks on calling :const:`~twitchAPI.eventsub.EventSub.stop()` |default| :code:`True`"""
        self._host: str = '0.0.0.0'
        self.__running = False
        self._startup_complete = False
        self.__callbacks = {}
        self._closing = False
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
            time.sleep(0.1)

    async def _keep_loop_alive(self):
        while not self._closing:
            await asyncio.sleep(0.1)

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
        # self.__hook_loop.call_soon_threadsafe(self.__hook_loop.stop)
        self.__hook_runner = None
        self.__running = False
        self.logger.debug('eventsub shut down')

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    def __build_request_header(self):
        token = self.__twitch.get_app_token()
        if token is None:
            raise TwitchAuthorizationException('no Authorization set!')
        return {
            'Client-ID': self.__client_id,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    async def __api_post_request(self, session, url: str, data: Union[dict, None] = None):
        headers = self.__build_request_header()
        return await session.post(url, headers=headers, json=data)

    def __add_callback(self, c_id: str, callback):
        self.__callbacks[c_id] = {'id': c_id, 'callback': callback, 'active': False}

    async def __activate_callback(self, c_id: str):
        if c_id not in self.__callbacks:
            self.logger.debug(f'callback for {c_id} arrived before confirmation, waiting...')
        while c_id not in self.__callbacks:
            await asyncio.sleep(0.1)
        self.__callbacks[c_id]['active'] = True

    async def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback) -> str:
        """"Subscribe to Twitch Topic"""
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError('callback needs to be a async function which takes one parameter')
        self.logger.debug(f'subscribe to {sub_type} version {sub_version} with condition {condition}')
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
        async with ClientSession(timeout=self.__twitch.session_timeout) as session:
            r_data = await self.__api_post_request(session, TWITCH_API_BASE_URL + 'eventsub/subscriptions', data=data)
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
        self.__add_callback(sub_id, callback)
        if self.wait_for_subscription_confirm:
            timeout = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=self.wait_for_subscription_confirm_timeout)
            while timeout >= datetime.datetime.utcnow():
                if self.__callbacks[sub_id]['active']:
                    return sub_id
                await asyncio.sleep(0.01)
            self.__callbacks.pop(sub_id, None)
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

    # ==================================================================================================================
    # HANDLERS
    # ==================================================================================================================

    # noinspection PyUnusedLocal
    @staticmethod
    async def __handle_default(request: 'web.Request'):
        return web.Response(text="pyTwitchAPI EventSub")

    async def __handle_challenge(self, request: 'web.Request', data: dict):
        self.logger.debug(f'received challenge for subscription {data.get("subscription").get("id")}')
        if not await self._verify_signature(request):
            self.logger.warning(f'message signature is not matching! Discarding message')
            return web.Response(status=403)
        await self.__activate_callback(data.get('subscription').get('id'))
        return web.Response(text=data.get('challenge'))

    async def __handle_callback(self, request: 'web.Request'):
        data: dict = await request.json()
        if data.get('challenge') is not None:
            return await self.__handle_challenge(request, data)
        sub_id = data.get('subscription', {}).get('id')
        callback = self.__callbacks.get(sub_id)
        if callback is None:
            self.logger.error(f'received event for unknown subscription with ID {sub_id}')
        else:
            if not await self._verify_signature(request):
                self.logger.warning(f'message signature is not matching! Discarding message')
                return web.Response(status=403)
            self.__hook_loop.create_task(callback['callback'](data))
        return web.Response(status=200)

    async def unsubscribe_all(self):
        """Unsubscribe from all subscriptions"""
        ret = await self.__twitch.get_eventsub_subscriptions()
        async for d in ret:
            try:
                await self.__twitch.delete_eventsub_subscription(d.id)
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {d.id}: {str(e)}')
        self.__callbacks.clear()

    async def unsubscribe_all_known(self):
        """Unsubscribe from all subscriptions known to this client."""
        for key, value in self.__callbacks.items():
            self.logger.debug(f'unsubscribe from event {key}')
            try:
                await self.__twitch.delete_eventsub_subscription(key)
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {key}: {str(e)}')
        self.__callbacks.clear()

    async def unsubscribe_topic(self, topic_id: str) -> bool:
        """Unsubscribe from a specific topic."""
        try:
            await self.__twitch.delete_eventsub_subscription(topic_id)
            self.__callbacks.pop(topic_id, None)
            return True
        except TwitchAPIException as e:
            self.logger.warning(f'failed to unsubscribe from {topic_id}: {str(e)}')
        return False

    async def listen_channel_update(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A broadcaster updates their channel properties e.g., category, title, mature flag, broadcast, or language.

        No Authentication required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.update', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_follow(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A specified channel receives a follow.

        .. warning:: This subscription is deprecated and will be removed on or soon after the 3rd of August 2023\n
            Please use :const:`~twitchAPI.eventsub.EventSub.listen_channel_follow_v2()`

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.follow', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_follow_v2(self,
                                       broadcaster_user_id: str,
                                       moderator_user_id: str,
                                       callback: CALLBACK_TYPE) -> str:
        """A specified channel receives a follow.

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_FOLLOWERS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow

        :param broadcaster_user_id: the id of the user you want to listen to
        :param moderator_user_id: The ID of the moderator of the channel you want to get follow notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.follow',
                                     '2',
                                     {'broadcaster_user_id': broadcaster_user_id, 'moderator_user_id': moderator_user_id},
                                     callback)

    async def listen_channel_subscribe(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A notification when a specified channel receives a subscriber. This does not include resubscribes.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscribe

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscribe', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_subscription_end(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A notification when a subscription to the specified channel ends.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_subscription_gift(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A notification when a viewer gives a gift subscription to one or more users in the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptiongift

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.gift', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_subscription_message(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A notification when a user sends a resubscription chat message in a specific channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionmessage

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.message',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_cheer(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A user cheers on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.BITS_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelcheer

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.cheer',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_raid(self,
                                  callback: CALLBACK_TYPE,
                                  to_broadcaster_user_id: Optional[str] = None,
                                  from_broadcaster_user_id: Optional[str] = None) -> str:
        """A broadcaster raids another broadcaster’s channel.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelraid

        :param from_broadcaster_user_id: The broadcaster user ID that created the channel raid you want to get notifications for.
        :param to_broadcaster_user_id: The broadcaster user ID that received the channel raid you want to get notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.raid',
                                     '1',
                                     remove_none_values({
                                         'from_broadcaster_user_id': from_broadcaster_user_id,
                                         'to_broadcaster_user_id': to_broadcaster_user_id}),
                                     callback)

    async def listen_channel_ban(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A viewer is banned from the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.ban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_unban(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A viewer is unbanned from the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelunban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.unban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_moderator_add(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """Moderator privileges were added to a user on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatoradd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.moderator.add',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_moderator_remove(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """Moderator privileges were removed from a user on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatorremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.moderator.remove',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_points_custom_reward_add(self, broadcaster_user_id: str,
                                                      callback: CALLBACK_TYPE) -> str:
        """A custom channel points reward has been created for the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.channel_points_custom_reward.add',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback)

    async def listen_channel_points_custom_reward_update(self,
                                                         broadcaster_user_id: str,
                                                         callback: CALLBACK_TYPE,
                                                         reward_id: Optional[str] = None) -> str:
        """A custom channel points reward has been updated for the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.channel_points_custom_reward.update',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback)

    async def listen_channel_points_custom_reward_remove(self,
                                                         broadcaster_user_id: str,
                                                         callback: CALLBACK_TYPE,
                                                         reward_id: Optional[str] = None) -> str:
        """A custom channel points reward has been removed from the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.channel_points_custom_reward.remove',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback)

    async def listen_channel_points_custom_reward_redemption_add(self,
                                                                 broadcaster_user_id: str,
                                                                 callback: CALLBACK_TYPE,
                                                                 reward_id: Optional[str] = None) -> str:
        """A viewer has redeemed a custom channel points reward on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.channel_points_custom_reward_redemption.add',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback)

    async def listen_channel_points_custom_reward_redemption_update(self,
                                                                    broadcaster_user_id: str,
                                                                    callback: CALLBACK_TYPE,
                                                                    reward_id: Optional[str] = None) -> str:
        """A redemption of a channel points custom reward has been updated for the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.channel_points_custom_reward_redemption.update',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback)

    async def listen_channel_poll_begin(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A poll started on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_poll_progress(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """Users respond to a poll on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_poll_end(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A poll ended on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_prediction_begin(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Prediction started on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_prediction_progress(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """Users participated in a Prediction on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_prediction_lock(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Prediction was locked on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionlock

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.lock', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_channel_prediction_end(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Prediction ended on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_drop_entitlement_grant(self,
                                            organisation_id: str,
                                            callback: CALLBACK_TYPE,
                                            category_id: Optional[str] = None,
                                            campaign_id: Optional[str] = None) -> str:
        """An entitlement for a Drop is granted to a user.

        App access token required. The client ID associated with the access token must be owned by a user who is part of the specified organization.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#dropentitlementgrant

        :param organisation_id: The organization ID of the organization that owns the game on the developer portal.
        :param category_id: The category (or game) ID of the game for which entitlement notifications will be received. |default| :code:`None`
        :param campaign_id: The campaign ID for a specific campaign for which entitlement notifications will be received. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('drop.entitlement.grant',
                                     '1',
                                     remove_none_values({
                                         'organization_id': organisation_id,
                                         'category_id': category_id,
                                         'campaign_id': campaign_id
                                     }),
                                     callback)

    async def listen_extension_bits_transaction_create(self,
                                                       extension_client_id: str,
                                                       callback: CALLBACK_TYPE) -> str:
        """A Bits transaction occurred for a specified Twitch Extension.

        The OAuth token client ID must match the Extension client ID.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#extensionbits_transactioncreate

        :param extension_client_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('extension.bits_transaction.create', '1', {'extension_client_id': extension_client_id}, callback)

    async def listen_goal_begin(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A goal begins on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_goal_progress(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A goal makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_goal_end(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A goal ends on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_hype_train_begin(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Hype Train begins on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_hype_train_progress(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Hype Train makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_hype_train_end(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """A Hype Train ends on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_stream_online(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """The specified broadcaster starts a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamonline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('stream.online', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_stream_offline(self, broadcaster_user_id: str, callback: CALLBACK_TYPE) -> str:
        """The specified broadcaster stops a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamoffline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('stream.offline', '1', {'broadcaster_user_id': broadcaster_user_id}, callback)

    async def listen_user_authorization_grant(self, client_id: str, callback: CALLBACK_TYPE) -> str:
        """A user’s authorization has been granted to your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationgrant

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.authorization.grant', '1', {'client_id': client_id}, callback)

    async def listen_user_authorization_revoke(self, client_id: str, callback: CALLBACK_TYPE) -> str:
        """A user’s authorization has been revoked for your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationrevoke

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.authorization.revoke', '1', {'client_id': client_id}, callback)

    async def listen_user_update(self, user_id: str, callback: CALLBACK_TYPE) -> str:
        """A user has updated their account.

        No authorization required. If you have the :const:`~twitchAPI.types.AuthScope.USER_READ_EMAIL` scope,
        the notification will include email field.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userupdate

        :param user_id: The user ID for the user you want update notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.update', '1', {'user_id': user_id}, callback)

    async def listen_channel_shield_mode_begin(self,
                                               broadcaster_user_id: str,
                                               moderator_user_id: str,
                                               callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the broadcaster activates Shield Mode.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modebegin

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they activate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shield_mode.begin', '1', param, callback)

    async def listen_channel_shield_mode_end(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the broadcaster deactivates Shield Mode.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modeend

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they deactivate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shield_mode.end', '1', param, callback)

    async def listen_channel_charity_campaign_start(self,
                                                    broadcaster_user_id: str,
                                                    callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the broadcaster starts a charity campaign.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstart

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they start a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.start', '1', param, callback)

    async def listen_channel_charity_campaign_progress(self,
                                                       broadcaster_user_id: str,
                                                       callback: CALLBACK_TYPE) -> str:
        """Sends notifications when progress is made towards the campaign’s goal or when the broadcaster changes the fundraising goal.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignprogress

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when their campaign makes progress or
                is updated.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.progress', '1', param, callback)

    async def listen_channel_charity_campaign_stop(self,
                                                   broadcaster_user_id: str,
                                                   callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the broadcaster stops a charity campaign.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstop

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they stop a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.stop', '1', param, callback)

    async def listen_channel_charity_campaign_donate(self,
                                                     broadcaster_user_id: str,
                                                     callback: CALLBACK_TYPE) -> str:
        """Sends a notification when a user donates to the broadcaster’s charity campaign.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaigndonate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when users donate to their campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.donate', '1', param, callback)

    async def listen_channel_shoutout_create(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the specified broadcaster sends a Shoutout.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutcreate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they send a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that gave the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shoutout.create', '1', param, callback)

    async def listen_channel_shoutout_receive(self,
                                              broadcaster_user_id: str,
                                              moderator_user_id: str,
                                              callback: CALLBACK_TYPE) -> str:
        """Sends a notification when the specified broadcaster receives a Shoutout.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutreceive

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they receive a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that received the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shoutout.receive', '1', param, callback)
