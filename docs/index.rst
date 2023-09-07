.. twitchAPI documentation master file, created by
   sphinx-quickstart on Sat Mar 28 12:49:23 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Twitch API
=================

This is a full implementation of the Twitch Helix API, PubSub, EventSub and Chat in python 3.7+.

On Github: https://github.com/Teekeks/pyTwitchAPI

On PyPi: https://pypi.org/project/twitchAPI/

Changelog: :doc:`changelog`


.. note:: There where major changes to the library with version 4, see the :doc:`v4-migration` to learn how to migrate.


Installation
============

Install using pip:

``pip install twitchAPI``

Support
=======

For Support please join the `Twitch API Discord server <https://discord.gg/tu2Dmc7gpd>`_.

Usage
=====

These are some basic usage examples, please visit the dedicated pages for more info.


TwitchAPI
---------

Calls to the Twitch Helix API, this is the base of this library.

See here for more info: :doc:`/modules/twitchAPI.twitch`

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    import asyncio

    async def twitch_example():
        # initialize the twitch instance, this will by default also create a app authentication for you
        twitch = await Twitch('app_id', 'app_secret')
        # call the API for the data of your twitch user
        # this returns a async generator that can be used to iterate over all results
        # but we are just interested in the first result
        # using the first helper makes this easy.
        user = await first(twitch.get_users(logins='your_twitch_user'))
        # print the ID of your user or do whatever else you want with it
        print(user.id)

    # run this example
    asyncio.run(twitch_example())



Authentication
--------------

The Twitch API knows 2 different authentications. App and User Authentication.
Which one you need (or if one at all) depends on what calls you want to use.

It's always good to get at least App authentication even for calls where you don't need it since the rate limits are way better for authenticated calls.

See here for more info about user authentication: :doc:`/modules/twitchAPI.oauth`

App Authentication
^^^^^^^^^^^^^^^^^^

App authentication is super simple, just do the following:

.. code-block:: python

   from twitchAPI.twitch import Twitch
   twitch = await Twitch('my_app_id', 'my_app_secret')


User Authentication
^^^^^^^^^^^^^^^^^^^

To get a user auth token, the user has to explicitly click "Authorize" on the twitch website. You can use various online services to generate a token or use my build in Authenticator.
For my Authenticator you have to add the following URL as a "OAuth Redirect URL": :code:`http://localhost:17563`
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`_.


.. code-block:: python

   from twitchAPI.twitch import Twitch
   from twitchAPI.oauth import UserAuthenticator
   from twitchAPI.type import AuthScope

   twitch = await Twitch('my_app_id', 'my_app_secret')

   target_scope = [AuthScope.BITS_READ]
   auth = UserAuthenticator(twitch, target_scope, force_verify=False)
   # this will open your default browser and prompt you with the twitch verification website
   token, refresh_token = await auth.authenticate()
   # add User authentication
   await twitch.set_user_authentication(token, target_scope, refresh_token)


You can reuse this token and use the refresh_token to renew it:

.. code-block:: python

   from twitchAPI.oauth import refresh_access_token
   new_token, new_refresh_token = await refresh_access_token('refresh_token', 'client_id', 'client_secret')


AuthToken refresh callback
^^^^^^^^^^^^^^^^^^^^^^^^^^

Optionally you can set a callback for both user access token refresh and app access token refresh.

.. code-block:: python

   from twitchAPI.twitch import Twitch

   async def user_refresh(token: str, refresh_token: str):
       print(f'my new user token is: {token}')

   async def app_refresh(token: str):
       print(f'my new app token is: {token}')

   twitch = await Twitch('my_app_id', 'my_app_secret')
   twitch.app_auth_refresh_callback = app_refresh
   twitch.user_auth_refresh_callback = user_refresh


EventSub
--------

EventSub lets you listen for events that happen on Twitch.

There are multiple EventSub transports available, used for different use cases.

See here for more info about EventSub in general and the different Transports, including code examples: :doc:`/modules/twitchAPI.eventsub`

PubSub
------

PubSub enables you to subscribe to a topic, for updates (e.g., when a user cheers in a channel).

See here for more info: :doc:`/modules/twitchAPI.pubsub`

.. code-block:: python

    from twitchAPI.pubsub import PubSub
    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.type import AuthScope
    from twitchAPI.oauth import UserAuthenticator
    import asyncio
    from pprint import pprint
    from uuid import UUID

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.WHISPERS_READ]
    TARGET_CHANNEL = 'teekeks42'

    async def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)


    async def run_example():
        # setting up Authentication and getting your user id
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, [AuthScope.WHISPERS_READ], force_verify=False)
        token, refresh_token = await auth.authenticate()
        # you can get your user auth token and user auth refresh token following the example in twitchAPI.oauth
        await twitch.set_user_authentication(token, [AuthScope.WHISPERS_READ], refresh_token)
        user = await first(twitch.get_users(logins=[TARGET_CHANNEL]))

        # starting up PubSub
        pubsub = PubSub(twitch)
        pubsub.start()
        # you can either start listening before or after you started pubsub.
        uuid = await pubsub.listen_whispers(user.id, callback_whisper)
        input('press ENTER to close...')
        # you do not need to unlisten to topics before stopping but you can listen and unlisten at any moment you want
        await pubsub.unlisten(uuid)
        pubsub.stop()
        await twitch.close()

    asyncio.run(run_example())

Chat
----

A simple twitch chat bot.
Chat bots can join channels, listen to chat and reply to messages, commands, subscriptions and many more.

See here for more info: :doc:`/modules/twitchAPI.chat`

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope, ChatEvent
    from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
    import asyncio

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
    TARGET_CHANNEL = 'teekeks42'


    # this will be called when the event READY is triggered, which will be on bot start
    async def on_ready(ready_event: EventData):
        print('Bot is ready for work, joining channels')
        # join our target channel, if you want to join multiple, either call join for each individually
        # or even better pass a list of channels as the argument
        await ready_event.chat.join_room(TARGET_CHANNEL)
        # you can do other bot initialization things in here


    # this will be called whenever a message in a channel was send by either the bot OR another user
    async def on_message(msg: ChatMessage):
        print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')


    # this will be called whenever someone subscribes to a channel
    async def on_sub(sub: ChatSub):
        print(f'New subscription in {sub.room.name}:\\n'
              f'  Type: {sub.sub_plan}\\n'
              f'  Message: {sub.sub_message}')


    # this will be called whenever the !reply command is issued
    async def test_command(cmd: ChatCommand):
        if len(cmd.parameter) == 0:
            await cmd.reply('you did not tell me what to reply with')
        else:
            await cmd.reply(f'{cmd.user.name}: {cmd.parameter}')


    # this is where we set up the bot
    async def run():
        # set up twitch api instance and add user authentication with some scopes
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

        # create chat instance
        chat = await Chat(twitch)

        # register the handlers for the events you want

        # listen to when the bot is done starting up and ready to join channels
        chat.register_event(ChatEvent.READY, on_ready)
        # listen to chat messages
        chat.register_event(ChatEvent.MESSAGE, on_message)
        # listen to channel subscriptions
        chat.register_event(ChatEvent.SUB, on_sub)
        # there are more events, you can view them all in this documentation

        # you can directly register commands and their handlers, this will register the !reply command
        chat.register_command('reply', test_command)


        # we are done with our setup, lets start this bot up!
        chat.start()

        # lets run till we press enter in the console
        try:
            input('press ENTER to stop\\n')
        finally:
            # now we can close the chat bot and the twitch api client
            chat.stop()
            await twitch.close()


    # lets run our setup
    asyncio.run(run())

Logging
=======

This module uses the `logging` module for creating Logs.
Valid loggers are:

.. list-table::
   :header-rows: 1

   * - Logger Name
     - Class
     - Variable
   * - :code:`twitchAPI.twitch`
     - :const:`~twitchAPI.twitch.Twitch`
     - :const:`~twitchAPI.twitch.Twitch.logger`
   * - :code:`twitchAPI.chat`
     - :const:`~twitchAPI.chat.Chat`
     - :const:`~twitchAPI.chat.Chat.logger`
   * - :code:`twitchAPI.eventsub.webhook`
     - :const:`~twitchAPI.eventsub.webhook.EventSubWebhook`
     - :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.logger`
   * - :code:`twitchAPI.eventsub.websocket`
     - :const:`~twitchAPI.eventsub.websocket.EventSubWebsocket`
     - :const:`~twitchAPI.eventsub.websocket.EventSubWebsocket.logger`
   * - :code:`twitchAPI.pubsub`
     - :const:`~twitchAPI.pubsub.PubSub`
     - :const:`~twitchAPI.pubsub.PubSub.logger`
   * - :code:`twitchAPI.oauth`
     - :const:`~twitchAPI.oauth.UserAuthenticator`
     - :const:`~twitchAPI.oauth.UserAuthenticator.logger`
   * - :code:`twitchAPI.oauth.storage_helper`
     - :const:`~twitchAPI.oauth.UserAuthenticationStorageHelper`
     - :const:`~twitchAPI.oauth.UserAuthenticationStorageHelper.logger`



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :doc:`tutorials`
* :doc:`changelog`
* :doc:`v3-migration`
* :doc:`v4-migration`


.. autosummary::
   :toctree: modules

   twitchAPI.twitch
   twitchAPI.eventsub
   twitchAPI.pubsub
   twitchAPI.chat
   twitchAPI.chat.middleware
   twitchAPI.oauth
   twitchAPI.type
   twitchAPI.helper
   twitchAPI.object

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :hidden:

   tutorials
   changelog
