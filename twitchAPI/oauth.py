#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
User OAuth Authenticator and helper functions
---------------------------------------------

This tool is an alternative to various online services that give you a user auth token.
It provides non-server and server options.

***************************************
Requirements for non-server environment
***************************************

Since this tool opens a browser tab for the Twitch authentication, you can only use this tool on enviroments that can
open a browser window and render the `<twitch.tv>`__ website.

For my authenticator you have to add the following URL as a "OAuth Redirect URL": :code:`http://localhost:17563`
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__.

***********************************
Requirements for server environment
***********************************

You need the user code provided by Twitch when the user logs-in at the url returned by :code:`return_auth_url`.

Create the UserAuthenticator with the URL of your webserver that will handle the redirect, and add it as a "OAuth Redirect URL"
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__.

************
Code example
************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.types import AuthScope

    twitch = Twitch('my_app_id', 'my_app_secret')

    target_scope = [AuthScope.BITS_READ]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    # this will open your default browser and prompt you with the twitch verification website
    token, refresh_token = auth.authenticate()
    # add User authentication
    twitch.set_user_authentication(token, target_scope, refresh_token)

********************
Class Documentation:
********************
"""
from .twitch import Twitch
from .helper import build_url, build_scope, get_uuid, TWITCH_AUTH_BASE_URL, fields_to_enum
from .types import AuthScope, InvalidRefreshTokenException, UnauthorizedException, TwitchAPIException
from typing import List, Union
import webbrowser
from aiohttp import web
import asyncio
from threading import Thread
from time import sleep
import requests
from concurrent.futures._base import CancelledError
from logging import getLogger, Logger


def refresh_access_token(refresh_token: str,
                         app_id: str,
                         app_secret: str):
    """Simple helper function for refreshing a user access token.

    :param str refresh_token: the current refresh_token
    :param str app_id: the id of your app
    :param str app_secret: the secret key of your app
    :return: access_token, refresh_token
    :raises ~twitchAPI.types.InvalidRefreshTokenException: if refresh token is invalid
    :raises ~twitchAPI.types.UnauthorizedException: if both refresh and access token are invalid (eg if the user changes
                their password of the app gets disconnected)
    :rtype: (str, str)
    """
    param = {
        'refresh_token': refresh_token,
        'client_id': app_id,
        'grant_type': 'refresh_token',
        'client_secret': app_secret
    }
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', {})
    result = requests.post(url, data=param)
    data = result.json()
    if data.get('status', 200) == 400:
        raise InvalidRefreshTokenException(data.get('message', ''))
    if data.get('status', 200) == 401:
        raise UnauthorizedException(data.get('message', ''))
    return data['access_token'], data['refresh_token']


def validate_token(access_token: str) -> dict:
    """Helper function for validating a user or app access token.

    https://dev.twitch.tv/docs/authentication#validating-requests

    :param str access_token: either a user or app OAuth access token
    :return: response from the api
    :rtype: dict
    """
    header = {'Authorization': f'OAuth {access_token}'}
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/validate', {})
    result = requests.get(url, headers=header)
    data = result.json()
    return fields_to_enum(data, ['scopes'], AuthScope, None)


def revoke_token(client_id: str, access_token: str) -> bool:
    """Helper function for revoking a user or app OAuth access token.

    https://dev.twitch.tv/docs/authentication#revoking-access-tokens

    :param str client_id: client id belonging to the access token
    :param str access_token: user or app OAuth access token
    :rtype: bool
    :return: :code:`True` if revoking succeeded, otherwise :code:`False`
    """
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/revoke', {
        'client_id': client_id,
        'token': access_token
    })
    result = requests.post(url)
    return result.status_code == 200


class UserAuthenticator:
    """Simple to use client for the Twitch User authentication flow.

        :param ~twitchAPI.twitch.Twitch twitch: A twitch instance
        :param list[~twitchAPI.types.AuthScope] scopes: List of the desired Auth scopes
        :param bool force_verify: If this is true, the user will always be prompted for authorization by twitch,
                    |default| :code:`False`
        :param str url: The reachable URL that will be opened in the browser.
                    |default| :code:`http://localhost:17563`

        :var int port: The port that will be used. |default| :code:`17653`
        :var str host: the host the webserver will bind to. |default| :code:`0.0.0.0`
       """

    __document: str = """<!DOCTYPE html>
 <html lang="en">
 <head>
     <meta charset="UTF-8">
     <title>pyTwitchAPI OAuth</title>
 </head>
 <body>
     <h1>Thanks for Authenticating with pyTwitchAPI!</h1>
 You may now close this page.
 </body>
 </html>"""

    __twitch: 'Twitch' = None
    port: int = 17563
    url: str = 'http://localhost:17563'
    host: str = '0.0.0.0'
    scopes: List[AuthScope] = []
    force_verify: bool = False
    __state: str = str(get_uuid())
    __logger: Logger = None

    __client_id: str = None

    __callback_func = None

    __server_running: bool = False
    __loop: Union['asyncio.AbstractEventLoop', None] = None
    __runner: Union['web.AppRunner', None] = None
    __thread: Union['threading.Thread', None] = None

    __user_token: Union[str, None] = None

    __can_close: bool = False

    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 force_verify: bool = False,
                 url: str = 'http://localhost:17563'):
        self.__twitch = twitch
        self.__client_id = twitch.app_id
        self.scopes = scopes
        self.force_verify = force_verify
        self.__logger = getLogger('twitchAPI.oauth')
        self.url = url

    def __build_auth_url(self):
        params = {
            'client_id': self.__twitch.app_id,
            'redirect_uri': self.url,
            'response_type': 'code',
            'scope': build_scope(self.scopes),
            'force_verify': str(self.force_verify).lower(),
            'state': self.__state
        }
        return build_url(TWITCH_AUTH_BASE_URL + 'oauth2/authorize', params)

    def __build_runner(self):
        app = web.Application()
        app.add_routes([web.get('/', self.__handle_callback)])
        return web.AppRunner(app)

    async def __run_check(self):
        while not self.__can_close:
            try:
                await asyncio.sleep(1)
            except (CancelledError, asyncio.CancelledError):
                pass
        for task in asyncio.all_tasks(self.__loop):
            task.cancel()

    def __run(self, runner: 'web.AppRunner'):
        self.__runner = runner
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)
        self.__loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, self.host, self.port)
        self.__loop.run_until_complete(site.start())
        self.__server_running = True
        self.__logger.info('running oauth Webserver')
        try:
            self.__loop.run_until_complete(self.__run_check())
        except (CancelledError, asyncio.CancelledError):
            pass

    def __start(self):
        self.__thread = Thread(target=self.__run, args=(self.__build_runner(),))
        self.__thread.start()

    def stop(self):
        """Manually stop the flow

        :rtype: None
        """
        self.__can_close = True

    async def __handle_callback(self, request: 'web.Request'):
        val = request.rel_url.query.get('state')
        self.__logger.debug(f'got callback with state {val}')
        # invalid state!
        if val != self.__state:
            return web.Response(status=401)
        self.__user_token = request.rel_url.query.get('code')
        if self.__user_token is None:
            # must provide code
            return web.Response(status=400)
        if self.__callback_func is not None:
            self.__callback_func(self.__user_token)
        return web.Response(text=self.__document, content_type='text/html')

    def return_auth_url(self):
        return self.__build_auth_url()

    def authenticate(self,
                     callback_func=None, user_token=None):
        """Start the user authentication flow\n
        If callback_func is not set, authenticate will wait till the authentication process finished and then return
        the access_token and the refresh_token
        If user_token is set, it will be used instead of launching the webserver and opening the browser

        :param callback_func: Function to call once the authentication finished.
        :param str user_token: Code obtained from twitch to request the access and refresh token.
        :return: None if callback_func is set, otherwise access_token and refresh_token
        :raises ~twitchAPI.types.TwitchAPIException: if authentication fails
        :rtype: None or (str, str)
        """
        self.__callback_func = callback_func

        if user_token is None:
            self.__start()
            # wait for the server to start up
            while not self.__server_running:
                sleep(0.01)
            # open in browser
            webbrowser.open(self.__build_auth_url(), new=2)
            while self.__user_token is None:
                sleep(0.01)
            # now we need to actually get the correct token
        else:
            self.__user_token = user_token

        param = {
            'client_id': self.__client_id,
            'client_secret': self.__twitch.app_secret,
            'code': self.__user_token,
            'grant_type': 'authorization_code',
            'redirect_uri': self.url
        }
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', param)
        response = requests.post(url)
        data: dict = response.json()
        if callback_func is None:
            self.stop()
            if data.get('access_token') is None:
                raise TwitchAPIException(f'Authentication failed:\n{str(data)}')
            return data['access_token'], data['refresh_token']
        elif user_token is not None:
            self.__callback_func(self.__user_token)
