Chat - Introduction to Middleware
=================================

In this tutorial, we will go over a few examples on how to use and write your own chat command middleware.

Basics
******

Command Middleware can be understood as a set of filters which decide if a chat command should be executed by a user.
A basic example would be the idea to limit the use of certain commands to just a few chat rooms or restricting the use of administrative commands to just the streamer.


There are two types of command middleware:

1. global command middleware: this will be used to check any command that might be run
2. single command middleware: this will only be used to check a single command if it might be run


Example setup
*************

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
        await cmd.reply('This is the second command!')


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
*****************

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
       await cmd.reply('This is the second command!')


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
*************************

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
       await cmd.reply('This is the second command!')


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


Using Execute Blocked Handlers
******************************

Execute blocked handlers are a function which will be called whenever the execution of a command was blocked.

You can define a default handler to be used for any middleware that blocks a command execution and/or set one per
middleware that will only be used when that specific middleware blocked the execution of a command.

Note: You can mix and match a default handler with middleware specific handlers as much as you want.

Using a default handler
-----------------------

A default handler will be called whenever the execution of a command is blocked by a middleware which has no specific handler set.

You can define a simple handler which just replies to the user as follows using the global middleware example:

:const:`handle_command_blocked()` will be called if the execution of either :code:`!one` or :code:`!two` is blocked, regardless by which of the two middlewares.

.. code-block:: python
   :linenos:
   :emphasize-lines: 23, 24, 37

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
       await cmd.reply('This is the second command!')


   async def handle_command_blocked(cmd: ChatCommand):
       await cmd.reply(f'You are not allowed to use {cmd.name}!')


   async def run():
       twitch = await Twitch(APP_ID, APP_SECRET)
       helper = UserAuthenticationStorageHelper(twitch, SCOPES)
       await helper.bind()
       chat = await Chat(twitch, initial_channel=TARGET_CHANNEL)
       chat.register_command_middleware(UserRestriction(allowed_users=['user1']))
       chat.register_command_middleware(ChannelRestriction(allowed_channel=['your_first_channel']))

       chat.register_command('one', command_one)
       chat.register_command('two', command_two)
       chat.default_command_execution_blocked_handler = handle_command_blocked

       chat.start()
       try:
           input('press Enter to shut down...\n')
       except KeyboardInterrupt:
           pass
       finally:
           chat.stop()
           await twitch.close()


   asyncio.run(run())

Using a middleware specific handler
-----------------------------------

A middleware specific handler can be used to change the response based on which middleware blocked the execution of a command.
Note that this can again be both set for command specific middleware as well as global middleware.
For this example we will only look at global middleware but the method is exactly the same for command specific one.

To set a middleware specific handler, you have to set :const:`~twitchAPI.chat.middleware.BaseCommandMiddleware.execute_blocked_handler`.
For the preimplemented middleware in this library, you can always pass this in the init of the middleware.

In the following example we will be responding different based on which middleware blocked the command.


.. code-block:: python
   :linenos:
   :emphasize-lines: 23, 24, 27, 28, 36, 37, 38, 39

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
       await cmd.reply('This is the second command!')


   async def handle_blocked_user(cmd: ChatCommand):
       await cmd.reply(f'Only user1 is allowed to use {cmd.name}!')


   async def handle_blocked_channel(cmd: ChatCommand):
       await cmd.reply(f'{cmd.name} can only be used in channel your_first_channel!')


   async def run():
       twitch = await Twitch(APP_ID, APP_SECRET)
       helper = UserAuthenticationStorageHelper(twitch, SCOPES)
       await helper.bind()
       chat = await Chat(twitch, initial_channel=TARGET_CHANNEL)
       chat.register_command_middleware(UserRestriction(allowed_users=['user1'],
                                                        execute_blocked_handler=handle_blocked_user))
       chat.register_command_middleware(ChannelRestriction(allowed_channel=['your_first_channel'],
                                                           execute_blocked_handler=handle_blocked_channel))

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


Write your own Middleware
*************************

You can also write your own middleware to implement custom logic, you only have to extend the class :const:`~twitchAPI.chat.middleware.BaseCommandMiddleware`.

In the following example, we will create a middleware which allows the command to execute in 50% of the times its executed.

.. code-block:: python

   from typing import Callable, Optional, Awaitable

   class MyOwnCoinFlipMiddleware(BaseCommandMiddleware):

      # it is best practice to add this part of the init function to be compatible with the default middlewares
      # but you can also leave this out should you know you dont need it
      def __init__(self, execute_blocked_handler: Optional[Callable[[ChatCommand], Awaitable[None]]] = None):
        self.execute_blocked_handler = execute_blocked_handler

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

