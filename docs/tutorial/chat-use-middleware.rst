Chat - Introduction to Middleware
=================================

In this tutorial, we will go over a few examples on how to use and write your own chat command middleware.

Basics
------

Command Middleware can be understood as a set of filters which decide if a chat command should be executed by a user.
A basic example would be the idea to limit the use of certain commands to just a few chat rooms or restricting the use of administrative commands to just the streamer.


There are two types of command middleware:

1. global command middleware: this will be used to check any command that might be run
2. single command middleware: this will only be used to check a single command if it might be run


Example setup
-------------

The following basic chat example will be used in this entire tutorial

.. code-block:: python
   :linenos:

    import asyncio
    from twitchAPI import Twitch
    from twitchAPI.chat import Chat, ChatCommand
    from twitchAPI.oauth import UserAuthenticationStorageHelper
    from twitchAPI.types import AuthScope


    APP_ID = 'your_app_id'
    APP_SECRET = 'your_app_secret'
    SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
    TARGET_CHANNEL = ['your_first_channel', 'your_second_channel']


    async def command_one(cmd: ChatCommand):
        await cmd.reply('This is the first command!')


    async def command_two(cmd: ChatCommand):
        await cmd.reply('This is the first command!')


    async def run():
        twitch = await Twitch(APP_ID, APP_SECRET)
        helper = UserAuthenticationStorageHelper(twitch, SCOPES)
        await helper.bind()
        chat = await Chat(twitch, initial_channel=TARGET_CHANNEL)

        chat.register_command('one', command_one)
        chat.register_command('two', command_two)

        chat.start()
        try:
            input('press Enter to shut down...\n')
        except KeyboardInterrupt:
            pass
        finally:
            chat.stop()
            await twitch.close()


    asyncio.run(run())


Global Middleware
-----------------

Given the above example, we now want to restrict the use of all commands in a way that only user :code:`user1` can use them and that they can only be used in :code:`your_first_channel`.

The highlighted lines in the code below show how easy it is to set this up:

.. code-block:: python
   :linenos:
   :emphasize-lines: 4,28,29

   import asyncio
   from twitchAPI import Twitch
   from twitchAPI.chat import Chat, ChatCommand
   from twitchAPI.chat.middleware import UserRestriction, ChannelRestriction
   from twitchAPI.oauth import UserAuthenticationStorageHelper
   from twitchAPI.types import AuthScope


   APP_ID = 'your_app_id'
   APP_SECRET = 'your_app_secret'
   SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
   TARGET_CHANNEL = ['your_first_channel', 'your_second_channel']


   async def command_one(cmd: ChatCommand):
       await cmd.reply('This is the first command!')


   async def command_two(cmd: ChatCommand):
       await cmd.reply('This is the first command!')


   async def run():
       twitch = await Twitch(APP_ID, APP_SECRET)
       helper = UserAuthenticationStorageHelper(twitch, SCOPES)
       await helper.bind()
       chat = await Chat(twitch, initial_channel=TARGET_CHANNEL)
       chat.register_command_middleware(UserRestriction(allowed_users=['user1']))
       chat.register_command_middleware(ChannelRestriction(allowed_channel=['your_first_channel']))

       chat.register_command('one', command_one)
       chat.register_command('two', command_two)

       chat.start()
       try:
           input('press Enter to shut down...\n')
       except KeyboardInterrupt:
           pass
       finally:
           chat.stop()
           await twitch.close()


   asyncio.run(run())

Single Command Middleware
-------------------------

Given the above example, we now want to only restrict :code:`!one` to be used by the streamer of the channel its executed in.

The highlighted lines in the code below show how easy it is to set this up:

.. code-block:: python
   :linenos:
   :emphasize-lines: 4, 29

   import asyncio
   from twitchAPI import Twitch
   from twitchAPI.chat import Chat, ChatCommand
   from twitchAPI.chat.middleware import StreamerOnly
   from twitchAPI.oauth import UserAuthenticationStorageHelper
   from twitchAPI.types import AuthScope


   APP_ID = 'your_app_id'
   APP_SECRET = 'your_app_secret'
   SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
   TARGET_CHANNEL = ['your_first_channel', 'your_second_channel']


   async def command_one(cmd: ChatCommand):
       await cmd.reply('This is the first command!')


   async def command_two(cmd: ChatCommand):
       await cmd.reply('This is the first command!')


   async def run():
       twitch = await Twitch(APP_ID, APP_SECRET)
       helper = UserAuthenticationStorageHelper(twitch, SCOPES)
       await helper.bind()
       chat = await Chat(twitch, initial_channel=TARGET_CHANNEL)

       chat.register_command('one', command_one, command_middleware=[StreamerOnly()])
       chat.register_command('two', command_two)

       chat.start()
       try:
           input('press Enter to shut down...\n')
       except KeyboardInterrupt:
           pass
       finally:
           chat.stop()
           await twitch.close()


   asyncio.run(run())

Write your own Middleware
-------------------------

You can also write your own middleware to implement custom logic, you only have to extend the class :const:`~twitchAPI.chat.middleware.BaseCommandMiddleware`.

In the following example, we will create a middleware which allows the command to execute in 50% of the times its executed.

.. code-block:: python

   class MyOwnCoinFlipMiddleware(BaseCommandMiddleware):

      async def can_execute(cmd: ChatCommand) -> bool:
         # add your own logic here, return True if the command should execute and False otherwise
         return random.choice([True, False])

      async def was_executed(cmd: ChatCommand):
         # this will be called whenever a command this Middleware is attached to was executed, use this to update your internal state
         # since this is a basic example, we do nothing here
         pass


Now use this middleware as any other:

.. code-block:: python

   chat.register_command('ban-me', execute_ban_me, command_middleware=[MyOwnCoinFlipMiddleware()])

