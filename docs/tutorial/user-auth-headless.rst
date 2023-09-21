Generate a User Auth Token Headless
===================================


This is a example on how to integrate :const:`~twitchAPI.oauth.UserAuthenticator` into your headless app.

This example uses the popular server software `flask <https://flask.palletsprojects.com/>`__ but it can easily adapted to other software.

.. note:: Please make sure to add your redirect URL (in this example the value of ``MY_URL``) as a "OAuth Redirect URL" `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__

While this example works as is, it is highly likely that you need to modify this heavily in accordance with your use case.

.. code-block:: python

    import asyncio
    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope, TwitchAPIException
    from flask import Flask, redirect, request

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    TARGET_SCOPE = [AuthScope.CHAT_EDIT, AuthScope.CHAT_READ]
    MY_URL = 'http://localhost:5000/login/confirm'


    app = Flask(__name__)
    twitch: Twitch
    auth: UserAuthenticator


    @app.route('/login')
    def login():
        return redirect(auth.return_auth_url())


    @app.route('/login/confirm')
    async def login_confirm():
        state = request.args.get('state')
        if state != auth.state:
            return 'Bad state', 401
        code = request.args.get('code')
        if code is None:
            return 'Missing code', 400
        try:
            token, refresh = await auth.authenticate(user_token=code)
            await twitch.set_user_authentication(token, TARGET_SCOPE, refresh)
        except TwitchAPIException as e:
            return 'Failed to generate auth token', 400
        return 'Sucessfully authenticated!'


    async def twitch_setup():
        global twitch, auth
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, TARGET_SCOPE, url=MY_URL)


    asyncio.run(twitch_setup())

