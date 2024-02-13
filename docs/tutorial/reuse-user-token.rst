Reuse user tokens with UserAuthenticationStorageHelper
======================================================

In this tutorial, we will look at different ways to use :const:`~twitchAPI.oauth.UserAuthenticationStorageHelper`.

Basic Use Case
-------------- 

This is the most basic example on how to use this helper.
It will store any generated token in a file named `user_token.json` in your current folder and automatically update that file with refreshed tokens.
Should the file not exists, the auth scope not match the one of the stored auth token or the token + refresh token no longer be valid, it will use :const:`~twitchAPI.oauth.UserAuthenticator` to generate a new one.

.. code-block:: python
   :linenos:

    from twitchAPI import Twitch
    from twitchAPI.oauth import UserAuthenticationStorageHelper
    from twitchAPI.types import AuthScope

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


    async def run():
        twitch = await Twitch(APP_ID, APP_SECRET)
        helper = UserAuthenticationStorageHelper(twitch, USER_SCOPE)
        await helper.bind()
        # do things

        await twitch.close()


    # lets run our setup
    asyncio.run(run())


Use a different file to store your token
----------------------------------------

You can specify a different file in which the token should be stored in like this:


.. code-block:: python
   :linenos:
   :emphasize-lines: 4, 15

    from twitchAPI import Twitch
    from twitchAPI.oauth import UserAuthenticationStorageHelper
    from twitchAPI.types import AuthScope
    from pathlib import PurePath

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


    async def run():
        twitch = await Twitch(APP_ID, APP_SECRET)
        helper = UserAuthenticationStorageHelper(twitch,
                                                 USER_SCOPE, 
                                                 storage_path=PurePath('/my/new/path/file.json'))
        await helper.bind()
        # do things

        await twitch.close()


    # lets run our setup
    asyncio.run(run())


Use custom token generation code
--------------------------------

Sometimes (for example for headless setups), the default UserAuthenticator is not good enough.
For these cases, you can use your own function.

.. code-block:: python
   :linenos:
   :emphasize-lines: 10, 11, 12, 18

    from twitchAPI import Twitch
    from twitchAPI.oauth import UserAuthenticationStorageHelper
    from twitchAPI.types import AuthScope

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


    async def my_token_generator(twitch: Twitch, target_scope: List[AuthScope]) -> (str, str):
        # generate new token + refresh token here and return it
        return 'token', 'refresh_token'

    async def run():
        twitch = await Twitch(APP_ID, APP_SECRET)
        helper = UserAuthenticationStorageHelper(twitch, 
                                                 USER_SCOPE, 
                                                 auth_generator_func=my_token_generator)
        await helper.bind()
        # do things

        await twitch.close()


    # lets run our setup
    asyncio.run(run())
