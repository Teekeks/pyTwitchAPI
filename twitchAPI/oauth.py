#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
User OAuth Authenticator and helper functions
=============================================

User Authenticator
------------------

:const:`~twitchAPI.oauth.UserAuthenticator` is an alternative to various online services that give you a user auth token.
It provides non-server and server options.

Requirements for non-server environment
***************************************

Since this tool opens a browser tab for the Twitch authentication, you can only use this tool on environments that can
open a browser window and render the `<twitch.tv>`__ website.

For my authenticator you have to add the following URL as a "OAuth Redirect URL": :code:`http://localhost:17563`
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__.

Requirements for server environment
***********************************

You need the user code provided by Twitch when the user logs-in at the url returned by :const:`~twitchAPI.oauth.UserAuthenticator.return_auth_url()`.

Create the UserAuthenticator with the URL of your webserver that will handle the redirect, and add it as a "OAuth Redirect URL"
You can set that `here in your twitch dev dashboard <https://dev.twitch.tv/console>`__.

.. seealso:: This tutorial has a more detailed example how to use UserAuthenticator on a headless server: :doc:`/tutorial/user-auth-headless`

.. seealso:: You may also use the CodeFlow to generate your access token headless :const:`~twitchAPI.oauth.CodeFlow`

Code example
************

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

User Authentication Storage Helper
----------------------------------

:const:`~twitchAPI.oauth.UserAuthenticationStorageHelper` provides a simplified way to store & reuse user tokens.

Code example
************

.. code-block:: python

      twitch = await Twitch(APP_ID, APP_SECRET)
      helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
      await helper.bind()"

.. seealso:: See :doc:`/tutorial/reuse-user-token` for more information.


Class Documentation
-------------------
"""
import datetime
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

__all__ = ['refresh_access_token', 'validate_token', 'get_user_info', 'revoke_token', 'CodeFlow', 'UserAuthenticator', 'UserAuthenticationStorageHelper']


async def refresh_access_token(refresh_token: str,
                               app_id: str,
                               app_secret: str,
                               session: Optional[aiohttp.ClientSession] = None,
                               auth_base_url: str = TWITCH_AUTH_BASE_URL):
    """Simple helper function for refreshing a user access token.

    :param str refresh_token: the current refresh_token
    :param str app_id: the id of your app
    :param str app_secret: the secret key of your app
    :param ~aiohttp.ClientSession session: optionally a active client session to be used for the web request to avoid having to open a new one
    :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
    :return: access_token, refresh_token
    :raises ~twitchAPI.type.InvalidRefreshTokenException: if refresh token is invalid
    :raises ~twitchAPI.type.UnauthorizedException: if both refresh and access token are invalid (eg if the user changes
                their password of the app gets disconnected)
    :rtype: (str, str)
    """
    param = {
        'refresh_token': refresh_token,
        'client_id': app_id,
        'grant_type': 'refresh_token',
        'client_secret': app_secret
    }
    url = build_url(auth_base_url + 'token', {})
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
                         session: Optional[aiohttp.ClientSession] = None,
                         auth_base_url: str = TWITCH_AUTH_BASE_URL) -> dict:
    """Helper function for validating a user or app access token.

    https://dev.twitch.tv/docs/authentication/validate-tokens

    :param access_token: either a user or app OAuth access token
    :param session: optionally a active client session to be used for the web request to avoid having to open a new one
    :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
    :return: response from the api
    """
    header = {'Authorization': f'OAuth {access_token}'}
    url = build_url(auth_base_url + 'validate', {})
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.get(url, headers=header) as result:
        data = await result.json()
    if session is None:
        await ses.close()
    return fields_to_enum(data, ['scopes'], AuthScope, None)


async def get_user_info(access_token: str,
                        session: Optional[aiohttp.ClientSession] = None,
                        auth_base_url: str = TWITCH_AUTH_BASE_URL) -> dict:
    """Helper function to get claims information from an OAuth2 access token.

    https://dev.twitch.tv/docs/authentication/getting-tokens-oidc/#getting-claims-information-from-an-access-token

    :param access_token: a OAuth2 access token
    :param session: optionally a active client session to be used for the web request to avoid having to open a new one
    :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
    :return: response from the API
    """
    header = {'Authorization': f'Bearer {access_token}',
              'Content-Type': 'application/json'}
    url = build_url(auth_base_url + 'userinfo', {})
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.get(url, headers=header) as result:
        data = await result.json()
    if session is None:
        await ses.close()
    return data


async def revoke_token(client_id: str,
                       access_token: str,
                       session: Optional[aiohttp.ClientSession] = None,
                       auth_base_url: str = TWITCH_AUTH_BASE_URL) -> bool:
    """Helper function for revoking a user or app OAuth access token.

    https://dev.twitch.tv/docs/authentication/revoke-tokens

    :param str client_id: client id belonging to the access token
    :param str access_token: user or app OAuth access token
    :param ~aiohttp.ClientSession session: optionally a active client session to be used for the web request to avoid having to open a new one
    :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
    :rtype: bool
    :return: :code:`True` if revoking succeeded, otherwise :code:`False`
    """
    url = build_url(auth_base_url + 'revoke', {
        'client_id': client_id,
        'token': access_token
    })
    ses = session if session is not None else aiohttp.ClientSession()
    async with ses.post(url) as result:
        ret = result.status == 200
    if session is None:
        await ses.close()
    return ret


class CodeFlow:
    """Basic implementation of the CodeFlow User Authentication.

    Example use:

    .. code-block:: python

        APP_ID = "my_app_id"
        APP_SECRET = "my_app_secret"
        USER_SCOPES = [AuthScope.BITS_READ, AuthScope.BITS_WRITE]

        twitch = await Twitch(APP_ID, APP_SECRET)
        code_flow = CodeFlow(twitch, USER_SCOPES)
        code, url = await code_flow.get_code()
        print(url)  # visit this url and complete the flow
        token, refresh = await code_flow.wait_for_auth_complete()
        await twitch.set_user_authentication(token, USER_SCOPES, refresh)
    """
    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 auth_base_url: str = TWITCH_AUTH_BASE_URL):
        """

        :param twitch: A twitch instance
        :param scopes: List of the desired Auth scopes
        :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
        """
        self._twitch: 'Twitch' = twitch
        self._client_id: str = twitch.app_id
        self._scopes: List[AuthScope] = scopes
        self.logger: Logger = getLogger('twitchAPI.oauth.code_flow')
        """The logger used for OAuth related log messages"""
        self.auth_base_url: str = auth_base_url
        self._device_code: Optional[str] = None
        self._expires_in: Optional[datetime.datetime] = None

    async def get_code(self) -> (str, str):
        """Requests a Code and URL from teh API to start the flow

        :return: The Code and URL used to further the flow
        """
        async with aiohttp.ClientSession(timeout=self._twitch.session_timeout) as session:
            data = {
                'client_id': self._client_id,
                'scopes': build_scope(self._scopes)
            }
            async with session.post(self.auth_base_url + 'device', data=data) as result:
                data = await result.json()
                self._device_code = data['device_code']
                self._expires_in = datetime.datetime.now() + datetime.timedelta(seconds=data['expires_in'])
                return data['user_code'], data['verification_uri']

    async def wait_for_auth_complete(self) -> (str, str):
        """Waits till the user completed the flow on teh website and then generates the tokens.

        :return: the generated access_token and refresh_token
        """
        if self._device_code is None:
            raise ValueError('Please start the code flow first using CodeFlow.get_code()')
        request_data = {
            'client_id': self._client_id,
            'scopes': build_scope(self._scopes),
            'device_code': self._device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }
        async with aiohttp.ClientSession(timeout=self._twitch.session_timeout) as session:
            while True:
                if datetime.datetime.now() > self._expires_in:
                    raise TimeoutError('Timed out waiting for auth complete')
                async with session.post(self.auth_base_url + 'token', data=request_data) as result:
                    result_data = await result.json()
                    if result_data.get('access_token') is not None:
                        # reset state for reuse before exit
                        self._device_code = None
                        self._expires_in = None
                        return result_data['access_token'], result_data['refresh_token']
                await asyncio.sleep(1)


class UserAuthenticator:
    """Simple to use client for the Twitch User authentication flow.
       """

    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 force_verify: bool = False,
                 url: str = 'http://localhost:17563',
                 host: str = '0.0.0.0',
                 port: int = 17563,
                 auth_base_url: str = TWITCH_AUTH_BASE_URL):
        """

        :param twitch: A twitch instance
        :param scopes: List of the desired Auth scopes
        :param force_verify: If this is true, the user will always be prompted for authorization by twitch |default| :code:`False`
        :param url: The reachable URL that will be opened in the browser. |default| :code:`http://localhost:17563`
        :param host: The host the webserver will bind to. |default| :code:`0.0.0.0`
        :param port: The port that will be used for the webserver. |default| :code:`17653`
        :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
        """
        self._twitch: 'Twitch' = twitch
        self._client_id: str = twitch.app_id
        self.scopes: List[AuthScope] = scopes
        self.force_verify: bool = force_verify
        self.logger: Logger = getLogger('twitchAPI.oauth')
        """The logger used for OAuth related log messages"""
        self.url = url
        self.auth_base_url: str = auth_base_url
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
        self.port: int = port
        """The port that will be used for the webserver. |default| :code:`17653`"""
        self.host: str = host
        """The host the webserver will bind to. |default| :code:`0.0.0.0`"""
        self.state: str = str(get_uuid())
        """The state to be used for identification, |default| a random UUID"""
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
        return build_url(self.auth_base_url + 'authorize', params)

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

    async def mock_authenticate(self, user_id: str) -> str:
        """Authenticate with a mocked auth flow via ``twitch-cli``

        For more info see :doc:`/tutorial/mocking`

        :param user_id: the id of the user to generate a auth token for
        :return: the user auth token
        """
        param = {
            'client_id': self._client_id,
            'client_secret': self._twitch.app_secret,
            'code': self._user_token,
            'user_id': user_id,
            'scope': build_scope(self.scopes),
            'grant_type': 'user_token'
        }
        url = build_url(self.auth_base_url + 'authorize', param)
        async with aiohttp.ClientSession(timeout=self._twitch.session_timeout) as session:
            async with session.post(url) as response:
                data: dict = await response.json()
        if data is None or data.get('access_token') is None:
            raise TwitchAPIException(f'Authentication failed:\n{str(data)}')
        return data['access_token']

    async def authenticate(self,
                           callback_func: Optional[Callable[[str, str], None]] = None,
                           user_token: Optional[str] = None,
                           browser_name: Optional[str] = None,
                           browser_new: int = 2,
                           use_browser: bool = True,
                           auth_url_callback: Optional[Callable[[str], Awaitable[None]]] = None):
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
        :param use_browser: controls if a browser should be opened.
                            If set to :const:`False`, the browser will not be opened and the URL to be opened will either be printed to the info log or
                            send to the specified callback function (controlled by :const:`~twitchAPI.oauth.UserAuthenticator.authenticate.params.auth_url_callback`)
                            |default|:code:`True`
        :param auth_url_callback: a async callback that will be called with the url to be used for the authentication flow should
                            :const:`~twitchAPI.oauth.UserAuthenticator.authenticate.params.use_browser` be :const:`False`.
                            If left as None, the URL will instead be printed to the info log
                            |default|:code:`None`
        :return: None if callback_func is set, otherwise access_token and refresh_token
        :raises ~twitchAPI.type.TwitchAPIException: if authentication fails
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
            if use_browser:
                # open in browser
                browser = webbrowser.get(browser_name)
                browser.open(self._build_auth_url(), new=browser_new)
            else:
                if auth_url_callback is not None:
                    await auth_url_callback(self._build_auth_url())
                else:
                    self.logger.info(f"To authenticate open: {self._build_auth_url()}")
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
        url = build_url(self.auth_base_url + 'token', param)
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
    See :doc:`/tutorial/reuse-user-token` for more detailed examples and use cases.

    Basic example use:

    .. code-block:: python

      twitch = await Twitch(APP_ID, APP_SECRET)
      helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
      await helper.bind()"""

    def __init__(self,
                 twitch: 'Twitch',
                 scopes: List[AuthScope],
                 storage_path: Optional[PurePath] = None,
                 auth_generator_func: Optional[Callable[['Twitch', List[AuthScope]], Awaitable[Tuple[str, str]]]] = None,
                 auth_base_url: str = TWITCH_AUTH_BASE_URL):
        self.twitch = twitch
        self.logger: Logger = getLogger('twitchAPI.oauth.storage_helper')
        """The logger used for OAuth Storage Helper related log messages"""
        self._target_scopes = scopes
        self.storage_path = storage_path if storage_path is not None else PurePath('user_token.json')
        self.auth_generator = auth_generator_func if auth_generator_func is not None else self._default_auth_gen
        self.auth_base_url: str = auth_base_url

    async def _default_auth_gen(self, twitch: 'Twitch', scopes: List[AuthScope]) -> (str, str):
        auth = UserAuthenticator(twitch, scopes, force_verify=True, auth_base_url=self.auth_base_url)
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
