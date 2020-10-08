#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
User OAuth Authenticator and helper functions
"""
from .twitch import Twitch
from .helper import build_url, build_scope, get_uuid, TWITCH_AUTH_BASE_URL
from .types import AuthScope
from typing import List, Union
import webbrowser
from aiohttp import web
import asyncio
from threading import Thread
from time import sleep
from os import path
import requests
from concurrent.futures._base import CancelledError


def refresh_access_token(refresh_token: str,
                         app_id: str,
                         app_secret: str):
    """Simple helper function for refreshing a user access token.

    :param refresh_token: the current refresh_token
    :type refresh_token: str
    :param app_id: the id of your app
    :type app_id: str
    :param app_secret: the secret key of your app
    :type app_secret: str
    :return: access_token, refresh_token
    :rtype: str, str
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
    return data['access_token'], data['refresh_token']


class UserAuthenticator:
    """Simple to use client for the Twitch User authentication flow.

    :param twitch: :class:`twitchAPI.twitch.Twitch` instance
    :param scopes: List of :class:`twitchAPI.types.AuthScope`, the desired Auth scopes
    """

    __twitch: 'Twitch' = None
    port: int = 17563
    url: str = 'localhost'
    scopes: List[AuthScope] = []
    force_verify: bool = False
    __state: str = str(get_uuid())

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
                 force_verify: bool = False):
        self.__twitch = twitch
        self.__client_id = twitch.app_id
        self.scopes = scopes
        self.force_verify = force_verify

    def __build_auth_url(self):
        params = {
            'client_id': self.__twitch.app_id,
            'redirect_uri': f'http://{self.url}:{self.port}',
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
            await asyncio.sleep(1)
        for task in asyncio.Task.all_tasks(self.__loop):
            task.cancel()

    def __run(self, runner: 'web.AppRunner'):
        self.__runner = runner
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)
        self.__loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, self.url, self.port)
        self.__loop.run_until_complete(site.start())
        self.__server_running = True
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
        # invalid state!
        if val != self.__state:
            return web.Response(status=401)
        self.__user_token = request.rel_url.query.get('code')
        if self.__user_token is None:
            # must provide code
            return web.Response(status=400)
        if self.__callback_func is not None:
            self.__callback_func(self.__user_token)
        fn = path.join(path.dirname(__file__), 'oauth.html')
        fd = ''
        with open(fn, 'r') as f:
            fd = f.read()
        return web.Response(text=fd, content_type='text/html')

    def authenticate(self,
                     callback_func=None):
        """Start the user authentication flow\n
        If callback_func is not set, authenticate will wait till the authentication process finnished and then return
        the access_token and the refresh_token

        :param callback_func: Function to call once the authentication finnished.
        :return: None if callback_func is set, otherwise access_token and refresh_token
        """
        self.__callback_func = callback_func
        self.__start()
        # wait for the server to start up
        while not self.__server_running:
            sleep(0.01)
        # open in browser
        webbrowser.open(self.__build_auth_url(), new=2)
        while self.__user_token is None:
            sleep(0.01)
        # now we need to actually get the correct token
        param = {
            'client_id': self.__client_id,
            'client_secret': self.__twitch.app_secret,
            'code': self.__user_token,
            'grant_type': 'authorization_code',
            'redirect_uri': f'http://{self.url}:{self.port}'
        }
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', param)
        response = requests.post(url)
        data = response.json()
        if callback_func is None:
            self.stop()
            return data['access_token'], data['refresh_token']
