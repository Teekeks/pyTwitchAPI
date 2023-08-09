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

You need the user code provided by Twitch when the user logs-in at the url returned by :const:`~twitchAPI.oauth.UserAuthenticator.return_auth_url()`.

Create the UserAuthenticator with the URL of your webserver that will handle the redirect, and add it as a "OAuth Redirect URL"
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__.

************
Code example
************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.types import AuthScope

    twitch = await Twitch('my_app_id', 'my_app_secret')

    target_scope = [AuthScope.BITS_READ]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    # this will open your default browser and prompt you with the twitch verification website
    token, refresh_token = await auth.authenticate()
    # add User authentication
    await twitch.set_user_authentication(token, target_scope, refresh_token)

*******************
Class Documentation
*******************
"""
import json
import os.path
from pathlib import PurePath

import aiohttp

from .twitch import Twitch
from .helper import build_url, build_scope, get_uuid, TWITCH_AUTH_BASE_URL, fields_to_enum
from .type import AuthScope, InvalidRefreshTokenException, UnauthorizedException, TwitchAPIException
from typing import Optional, Callable, Awaitable, Tuple
import webbrowser
from aiohttp import web
import asyncio
from threading import Thread
from concurrent.futures import CancelledError
from logging import getLogger, Logger

from typing import List, Union

__all__ = ['refresh_access_token', 'validate_token', 'get_user_info', 'revoke_token', 'UserAuthenticator', 'UserAuthenticationStorageHelper']


async def refresh_access_token(refresh_token: str,
                               app_id: str,
                               app_secret: str,
                               session: Optional[aiohttp.ClientSession] = None):
    """Simple helper function for refreshing a user access token.

    :param str refresh_token: the current refresh_token
    :param str app_id: the id of your app
    :param str app_secret: the secret key of your app
    :param ~aiohttp.ClientSession session: optionally a active client session to be used for the web request to avoid having to open a new one
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
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.post(url, data=param) as result:
        data = await result.json()
    if session is None:
        await ses.close()
    if data.get('status', 200) == 400:
        raise InvalidRefreshTokenException(data.get('message', ''))
    if data.get('status', 200) == 401:
        raise UnauthorizedException(data.get('message', ''))
    return data['access_token'], data['refresh_token']


async def validate_token(access_token: str,
                         session: Optional[aiohttp.ClientSession] = None) -> dict:
    """Helper function for validating a user or app access token.

    https://dev.twitch.tv/docs/authentication/validate-tokens

    :param access_token: either a user or app OAuth access token
    :param session: optionally a active client session to be used for the web request to avoid having to open a new one
    :return: response from the api
    """
    header = {'Authorization': f'OAuth {access_token}'}
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/validate', {})
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.get(url, headers=header) as result:
        data = await result.json()
    if session is None:
        await ses.close()
    return fields_to_enum(data, ['scopes'], AuthScope, None)


async def get_user_info(access_token: str,
                        session: Optional[aiohttp.ClientSession] = None) -> dict:
    """Helper function to get claims information from an OAuth2 access token.

    https://dev.twitch.tv/docs/authentication/getting-tokens-oidc/#getting-claims-information-from-an-access-token

    :param access_token: a OAuth2 access token
    :param session: optionally a active client session to be used for the web request to avoid having to open a new one
    :return: response from the API
    """
    header = {'Authorization': f'Bearer {access_token}',
              'Content-Type': 'application/json'}
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/userinfo', {})
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.get(url, headers=header) as result:
        data = await result.json()
    if session is None:
        await ses.close()
    return data


async def revoke_token(client_id: str,
                       access_token: str,
                       session: Optional[aiohttp.ClientSession] = None) -> bool:
    """Helper function for revoking a user or app OAuth access token.

    https://dev.twitch.tv/docs/authentication/revoke-tokens

    :param str client_id: client id belonging to the access token
    :param str access_token: user or app OAuth access token
    :param ~aiohttp.ClientSession session: optionally a active client session to be used for the web request to avoid having to open a new one
    :rtype: bool
    :return: :code:`True` if revoking succeeded, otherwise :code:`False`
    """
    url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/revoke', {
        'client_id': client_id,
        'token': access_token
    })
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.post(url) as result:
        ret = result.status == 200
    if session is None:
        await ses.close()
    return ret


class UserAuthenticator:
    """Simple to use client for the Twitch User authentication flow.
       """

    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 force_verify: bool = False,
                 url: str = 'http://localhost:17563'):
        """

        :param twitch: A twitch instance
        :param scopes: List of the desired Auth scopes
        :param force_verify: If this is true, the user will always be prompted for authorization by twitch |default| :code:`False`
        :param url: The reachable URL that will be opened in the browser. |default| :code:`http://localhost:17563`
        """
        self._twitch: 'Twitch' = twitch
        self._client_id: str = twitch.app_id
        self.scopes: List[AuthScope] = scopes
        self.force_verify: bool = force_verify
        self.logger: Logger = getLogger('twitchAPI.oauth')
        """The logger used for OAuth related log messages"""
        self.url = url
        self.document: str = """<!DOCTYPE html>
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
        """The document that will be rendered at the end of the flow"""
        self.port: int = 17563
        """The port that will be used. |default| :code:`17653`"""
        self.host: str = '0.0.0.0'
        """the host the webserver will bind to. |default| :code:`0.0.0.0`"""
        self.state: str = str(get_uuid())
        self._callback_func = None
        self._server_running: bool = False
        self._loop: Union[asyncio.AbstractEventLoop, None] = None
        self._runner: Union[web.AppRunner, None] = None
        self._thread: Union[Thread, None] = None
        self._user_token: Union[str, None] = None
        self._can_close: bool = False
        self._is_closed = False

    def _build_auth_url(self):
        params = {
            'client_id': self._twitch.app_id,
            'redirect_uri': self.url,
            'response_type': 'code',
            'scope': build_scope(self.scopes),
            'force_verify': str(self.force_verify).lower(),
            'state': self.state
        }
        return build_url(TWITCH_AUTH_BASE_URL + 'oauth2/authorize', params)

    def _build_runner(self):
        app = web.Application()
        app.add_routes([web.get('/', self._handle_callback)])
        return web.AppRunner(app)

    async def _run_check(self):
        while not self._can_close:
            await asyncio.sleep(0.1)
        await self._runner.shutdown()
        await self._runner.cleanup()
        self.logger.info('shutting down oauth Webserver')
        self._is_closed = True

    def _run(self, runner: web.AppRunner):
        self._runner = runner
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, self.host, self.port)
        self._loop.run_until_complete(site.start())
        self._server_running = True
        self.logger.info('running oauth Webserver')
        try:
            self._loop.run_until_complete(self._run_check())
        except (CancelledError, asyncio.CancelledError):
            pass

    def _start(self):
        self._thread = Thread(target=self._run, args=(self._build_runner(),))
        self._thread.start()

    def stop(self):
        """Manually stop the flow

        :rtype: None
        """
        self._can_close = True

    async def _handle_callback(self, request: web.Request):
        val = request.rel_url.query.get('state')
        self.logger.debug(f'got callback with state {val}')
        # invalid state!
        if val != self.state:
            return web.Response(status=401)
        self._user_token = request.rel_url.query.get('code')
        if self._user_token is None:
            # must provide code
            return web.Response(status=400)
        if self._callback_func is not None:
            self._callback_func(self._user_token)
        return web.Response(text=self.document, content_type='text/html')

    def return_auth_url(self):
        """Returns the URL that will authenticate the app, used for headless server environments."""
        return self._build_auth_url()

    async def authenticate(self,
                           callback_func: Optional[Callable[[str, str], None]] = None,
                           user_token: Optional[str] = None,
                           browser_name: Optional[str] = None,
                           browser_new: int = 2):
        """Start the user authentication flow\n
        If callback_func is not set, authenticate will wait till the authentication process finished and then return
        the access_token and the refresh_token
        If user_token is set, it will be used instead of launching the webserver and opening the browser

        :param callback_func: Function to call once the authentication finished.
        :param user_token: Code obtained from twitch to request the access and refresh token.
        :param browser_name: The browser that should be used, None means that the system default is used.
                            See `the webbrowser documentation <https://docs.python.org/3/library/webbrowser.html#webbrowser.register>`__ for more info
                            |default|:code:`None`
        :param browser_new: controls in which way the link will be opened in the browser.
                            See `the webbrowser documentation <https://docs.python.org/3/library/webbrowser.html#webbrowser.open>`__ for more info
                            |default|:code:`2`
        :return: None if callback_func is set, otherwise access_token and refresh_token
        :raises ~twitchAPI.types.TwitchAPIException: if authentication fails
        :rtype: None or (str, str)
        """
        self._callback_func = callback_func
        self._can_close = False
        self._user_token = None
        self._is_closed = False

        if user_token is None:
            self._start()
            # wait for the server to start up
            while not self._server_running:
                await asyncio.sleep(0.01)
            # open in browser
            browser = webbrowser.get(browser_name)
            browser.open(self._build_auth_url(), new=browser_new)
            while self._user_token is None:
                await asyncio.sleep(0.01)
            # now we need to actually get the correct token
        else:
            self._user_token = user_token
            self._is_closed = True

        param = {
            'client_id': self._client_id,
            'client_secret': self._twitch.app_secret,
            'code': self._user_token,
            'grant_type': 'authorization_code',
            'redirect_uri': self.url
        }
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', param)
        async with aiohttp.ClientSession(timeout=self._twitch.session_timeout) as session:
            async with session.post(url) as response:
                data: dict = await response.json()
        if callback_func is None:
            self.stop()
            while not self._is_closed:
                await asyncio.sleep(0.1)
            if data.get('access_token') is None:
                raise TwitchAPIException(f'Authentication failed:\n{str(data)}')
            return data['access_token'], data['refresh_token']
        elif user_token is not None:
            self._callback_func(data['access_token'], data['refresh_token'])


class UserAuthenticationStorageHelper:
    """Helper for automating the generation and storage of a user auth token.\n
    See Tutorial for more detailed examples and use cases.

    Basic example use:

    .. code-block:: python

      twitch = await Twitch(APP_ID, APP_SECRET)
      helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
      await helper.bind()"""

    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 storage_path: Optional[PurePath] = None,
                 auth_generator_func: Optional[Callable[['Twitch', List[AuthScope]], Awaitable[Tuple[str, str]]]] = None):
        self.twitch = twitch
        self.logger: Logger = getLogger('twitchAPI.oauth.storage_helper')
        self._target_scopes = scopes
        self.storage_path = storage_path if storage_path is not None else PurePath('user_token.json')
        self.auth_generator = auth_generator_func if auth_generator_func is not None else self._default_auth_gen

    @staticmethod
    async def _default_auth_gen(twitch: 'Twitch', scopes: List[AuthScope]) -> (str, str):
        auth = UserAuthenticator(twitch, scopes, force_verify=True)
        return await auth.authenticate()

    async def _update_stored_tokens(self, token: str, refresh_token: str):
        self.logger.info('user token got refreshed and stored')
        with open(self.storage_path, 'w') as _f:
            json.dump({'token': token, 'refresh': refresh_token}, _f)

    async def bind(self):
        """Bind the helper to the provided instance of twitch and sets the user authentication."""
        self.twitch.user_auth_refresh_callback = self._update_stored_tokens
        needs_auth = True
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as _f:
                    creds = json.load(_f)
                await self.twitch.set_user_authentication(creds['token'], self._target_scopes, creds['refresh'])
            except:
                self.logger.info('stored token invalid, refreshing...')
            else:
                needs_auth = False
        if needs_auth:
            token, refresh_token = await self.auth_generator(self.twitch, self._target_scopes)
            with open(self.storage_path, 'w') as _f:
                json.dump({'token': token, 'refresh': refresh_token}, _f)
            await self.twitch.set_user_authentication(token, self._target_scopes, refresh_token)
