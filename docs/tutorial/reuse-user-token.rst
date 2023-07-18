Reuse user tokens
=================

.. note:: This tutorial is still being worked on!

In this quick tutorial we will learn how to store and reuse a generated user token.
This is usefull in situations where you dont want to log in to twitch every time you restart your program.

Lets look at this basic setup for starting a chat bot:

.. code-block:: python

    from twitchAPI import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.types import AuthScope
    from twitchAPI.chat import Chat
    import asyncio

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


    async def run():
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

        # do things
        await twitch.stop()


    # lets run our setup
    asyncio.run(run())



