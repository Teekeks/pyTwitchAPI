Mocking with twitch-cli
=======================

Twitch CLI is a tool provided by twitch which can be used to mock API calls and EventSub.

To get started, first install and set up ``twitch-cli`` as described here: https://dev.twitch.tv/docs/cli/


Basic setup
-----------

First, run ``twitch mock-api generate`` once and note down the Client ID and secret as well as the ID from the line reading `User ID 53100947 has all applicable units`.

To run the mock server, run ``twitch mock-api start``

Mocking App Authentication and API
----------------------------------

The following code example sets us up with app auth and uses the mock API to get user information:

.. code-block:: python

    import asyncio
    from twitchAPI.helper import first
    from twitchAPI.twitch import Twitch

    CLIENT_ID = 'GENERATED_CLIENT_ID'
    CLIENT_SECRET = 'GENERATED_CLIENT_SECRET'
    USER_ID = '53100947'


    async def run():
        twitch = await Twitch(CLIENT_ID,
                              CLIENT_SECRET,
                              base_url='http://localhost:8080/mock/',
                              auth_base_url='http://localhost:8080/auth/')
        user = await first(twitch.get_users(user_ids=USER_ID))
        print(user.login)
        await twitch.close()


    asyncio.run(run())


Mocking User Authentication
---------------------------

In the following example you see how to set up mocking with a user authentication.

Note that :const:`~twitchAPI.twitch.Twitch.auto_refresh_auth` has to be set to `False` since the mock API does not return a refresh token.

.. code-block:: python

    import asyncio
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.helper import first
    from twitchAPI.twitch import Twitch

    CLIENT_ID = 'GENERATED_CLIENT_ID'
    CLIENT_SECRET = 'GENERATED_CLIENT_SECRET'
    USER_ID = '53100947'


    async def run():
        twitch = await Twitch(CLIENT_ID,
                              CLIENT_SECRET,
                              base_url='http://localhost:8080/mock/',
                              auth_base_url='http://localhost:8080/auth/')
        twitch.auto_refresh_auth = False
        auth = UserAuthenticator(twitch, [], auth_base_url='http://localhost:8080/auth/')
        token = await auth.mock_authenticate(USER_ID)
        await twitch.set_user_authentication(token, [])
        user = await first(twitch.get_users())
        print(user.login)
        await twitch.close()


    asyncio.run(run())

Mocking EventSub Webhook
------------------------

Since the EventSub subscription endpoints are not mocked in twitch-cli, we need to subscribe to events on the live api.
But we can then trigger events from within twitch-cli.

The following example subscribes to the ``channel.subscribe`` event and then prints the command to be used to trigger the event via twitch-cli to console.

.. code-block:: python

    import asyncio
    from twitchAPI.oauth import UserAuthenticationStorageHelper
    from twitchAPI.eventsub.webhook import EventSubWebhook
    from twitchAPI.object.eventsub import ChannelSubscribeEvent
    from twitchAPI.helper import first
    from twitchAPI.twitch import Twitch
    from twitchAPI.type import AuthScope

    CLIENT_ID = 'REAL_CLIENT_ID'
    CLIENT_SECRET = 'REAL_CLIENT_SECRET'
    EVENTSUB_URL = 'https://my.eventsub.url'


    async def on_subscribe(data: ChannelSubscribeEvent):
        print(f'{data.event.user_name} just subscribed!')


    async def run():
        twitch = await Twitch(CLIENT_ID,
                              CLIENT_SECRET)
        auth = UserAuthenticationStorageHelper(twitch, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS])
        await auth.bind()
        user = await first(twitch.get_users())
        eventsub = EventSubWebhook(EVENTSUB_URL, 8080, twitch)
        eventsub.start()
        sub_id = await eventsub.listen_channel_subscribe(user.id, on_subscribe)
        print(f'twitch event trigger channel.subscribe -F {EVENTSUB_URL}/callback -t {user.id} -u {sub_id} -s {eventsub.secret}')

        try:
            input('press ENTER to stop')
        finally:
            await eventsub.stop()
            await twitch.close()


    asyncio.run(run())


Mocking EventSub Websocket
--------------------------

For EventSub Websocket to work, you first have to run the following command to start a websocket server in addition to the API server: ``twitch event websocket start``

We once again mock both the app and user auth.

The following example subscribes to the ``channel.subscribe`` event and then prints the command to be used to trigger the event via twitch-cli to console.

.. code-block:: python

    import asyncio
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.eventsub.websocket import EventSubWebsocket
    from twitchAPI.object.eventsub import ChannelSubscribeEvent
    from twitchAPI.helper import first
    from twitchAPI.twitch import Twitch
    from twitchAPI.type import AuthScope

    CLIENT_ID = 'GENERATED_CLIENT_ID'
    CLIENT_SECRET = 'GENERATED_CLIENT_SECRET'
    USER_ID = '53100947'


    async def on_subscribe(data: ChannelSubscribeEvent):
        print(f'{data.event.user_name} just subscribed!')


    async def run():
        twitch = await Twitch(CLIENT_ID,
                              CLIENT_SECRET,
                              base_url='http://localhost:8080/mock/',
                              auth_base_url='http://localhost:8080/auth/')
        twitch.auto_refresh_auth = False
        auth = UserAuthenticator(twitch, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS], auth_base_url='http://localhost:8080/auth/')
        token = await auth.mock_authenticate(USER_ID)
        await twitch.set_user_authentication(token, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS])
        user = await first(twitch.get_users())
        eventsub = EventSubWebsocket(twitch,
                                     connection_url='ws://127.0.0.1:8080/ws',
                                     subscription_url='http://127.0.0.1:8080/')
        eventsub.start()
        sub_id = await eventsub.listen_channel_subscribe(user.id, on_subscribe)
        print(f'twitch event trigger channel.subscribe -t {user.id} -u {sub_id} -T websocket')

        try:
            input('press ENTER to stop\n')
        finally:
            await eventsub.stop()
            await twitch.close()


    asyncio.run(run())

