.. twitchAPI documentation master file, created by
   sphinx-quickstart on Sat Mar 28 12:49:23 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Twitch API
=====================================

This is a full implementation of the Twitch Helix API, its Webhook, PubSub and EventSub in python 3.7+.

On Github: https://github.com/Teekeks/pyTwitchAPI

On PyPi: https://pypi.org/project/twitchAPI/

Visit the :doc:`changelog` to see what has changed.

Installation
============

Install using pip:

```pip install twitchAPI```

Support
=======

For Support please join the `Twitch API Discord server <https://discord.gg/tu2Dmc7gpd>`_.

Usage
=====

These are some basic usage examples, please visit the dedicated pages for more info.


TwitchAPI
---------

Calls to the Twitch Helix API, this is the base of this library.

See here for more info: `twitchAPI.twitch <modules/twitchAPI.twitch.html>`_

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



EventSub
--------

Implementation of EventSub.

See here for more info: `twitchAPI.eventsub <modules/twitchAPI.eventsub.html>`_

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.eventsub import EventSub
    import asyncio


    TARGET_USERNAME = 'target_username_here'
    EVENTSUB_URL = 'https://url.to.your.webhook.com'
    APP_ID = 'your_app_id'
    APP_SECRET = 'your_app_secret'


    async def on_follow(data: dict):
        # our event happend, lets do things with the data we got!
        print(data)


    async def eventsub_example():
        # create the api instance and get the ID of the target user
        twitch = await Twitch(APP_ID, APP_SECRET)
        user = await first(twitch.get_users(logins=TARGET_USERNAME))

        # basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
        event_sub = EventSub(EVENTSUB_URL, APP_ID, 8080, twitch)

        # unsubscribe from all old events that might still be there
        # this will ensure we have a clean slate
        await event_sub.unsubscribe_all()
        # start the eventsub client
        event_sub.start()
        # subscribing to the desired eventsub hook for our user
        # the given function will be called every time this event is triggered
        await event_sub.listen_channel_follow(user.id, on_follow)

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

PubSub
------

Implementation of PubSub.

See here for more info: `twitchAPI.pubsub <modules/twitchAPI.pubsub.html>`_

.. code-block:: python

    from twitchAPI.pubsub import PubSub
    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    from twitchAPI.types import AuthScope
    import asyncio
    from pprint import pprint
    from uuid import UUID

    def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)


    async def run_example():
        # setting up Authentication and getting your user id
        twitch = await Twitch('my_app_id', 'my_app_secret')
        # you can get your user auth token and user auth refresh token following the example in twitchAPI.oauth
        await twitch.set_user_authentication('my_user_auth_token', [AuthScope.WHISPERS_READ], 'my_user_auth_refresh_token')
        user_id = await first(twitch.get_users(logins=['my_username'])).id

        # starting up PubSub
        pubsub = PubSub(twitch)
        pubsub.start()
        # you can either start listening before or after you started pubsub.
        uuid = pubsub.listen_whispers(user_id, callback_whisper)
        input('press ENTER to close...')
        # you do not need to unlisten to topics before stopping but you can listen and unlisten at any moment you want
        pubsub.unlisten(uuid)
        pubsub.stop()
        await twitch.close()

    asyncio.run(run_example())

Chat
----

A Twitch Chat Bot.

See here for more info: `twitchAPI.chat <modules/twitchAPI.chat.html>`_

.. code-block:: python

    from twitchAPI import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.types import AuthScope, ChatEvent
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
        ready_event.chat.join(TARGET_CHANNEL)
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

* `twitchAPI.twitch`
* `twitchAPI.eventsub`
* `twitchAPI.pubsub`
* `twitchAPI.chat`
* `twitchAPI.oauth`

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :doc:`changelog`


.. autosummary::
   :toctree: modules

   twitchAPI.twitch
   twitchAPI.eventsub
   twitchAPI.pubsub
   twitchAPI.chat
   twitchAPI.oauth
   twitchAPI.types
   twitchAPI.helper
   twitchAPI.object
