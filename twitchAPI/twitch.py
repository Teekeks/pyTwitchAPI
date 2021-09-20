#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
The Twitch API client
---------------------

This is the base of this library, it handles authentication renewal, error handling and permission management.

Look at the `Twitch API reference <https://dev.twitch.tv/docs/api/reference>`__ for a more detailed documentation on
what each endpoint does.

**************
Example Usage:
**************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from pprint import pprint
    twitch = Twitch('my_app_key', 'my_app_secret')
    pprint(twitch.get_users(logins=['your_twitch_username']))


**************
Authentication
**************

The Twitch API knows 2 different authentications. App and User Authentication.
Which one you need (or if one at all) depends on what calls you want to use.

Its always good to get at least App authentication even for calls where you don't need it since the rate limits are way
better for authenticated calls.


App Authentication
==================

By default, The lib will try to attempt to create a App Authentication on Initialization:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = Twitch('my_app_id', 'my_app_secret')

You can set a Auth Scope like this:

.. code-block:: python

    from twitchAPI.twitch import Twitch, AuthScope
    twitch = Twitch('my_app_id', 'my_app_secret', target_app_auth_scope=[AuthScope.USER_EDIT])

If you want to change the AuthScope later use this:

.. code-block:: python

    twitch.authenticate_app(my_new_scope)


If you don't want to use App Authentication, Initialize like this:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = Twitch('my_app_id', authenticate_app=False)


User Authentication
===================

Only use a user auth token, use this:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = Twitch('my_app_id', authenticate_app=False)
    # make sure to set the second parameter as the scope used to generate the token
    twitch.set_user_authentication('token', [], 'refresh_token')


Use both App and user Authentication:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = Twitch('my_app_id', 'my_app_secret')
    # make sure to set the second parameter as the scope used to generate the token
    twitch.set_user_authentication('token', [], 'refresh_token')


To get a user auth token, the user has to explicitly click "Authorize" on the twitch website. You can use various online
services to generate a token or use my build in authenticator.

See :obj:`twitchAPI.oauth` for more info on my build in authenticator.

Authentication refresh callback
===============================

Optionally you can set a callback for both user access token refresh and app access token refresh.

.. code-block:: python

    from twitchAPI.twitch import Twitch

    def user_refresh(token: str, refresh_token: str):
        print(f'my new user token is: {token}')

    def app_refresh(token: str):
        print(f'my new app token is: {token}')

    twitch = Twitch('my_app_id', 'my_app_secret')
    twitch.app_auth_refresh_callback = app_refresh
    twitch.user_auth_refresh_callback = user_refresh

********************
Class Documentation:
********************
"""
import requests
from typing import Union, List, Optional, Callable
from .helper import build_url, TWITCH_API_BASE_URL, TWITCH_AUTH_BASE_URL, make_fields_datetime, build_scope, \
    fields_to_enum, enum_value_or_none, datetime_to_str, remove_none_values
from datetime import datetime
from logging import getLogger, Logger
from .types import *


class Twitch:
    """
    Twitch API client

    :param str app_id: Your app id
    :param str app_secret: Your app secret, leave as None if you only want to use User Authentication
            |default| :code:`None`
    :param bool authenticate_app: If true, auto generate a app token on startup |default| :code:`True`
    :param list[~twitchAPI.types.AuthScope] target_app_auth_scope: AuthScope to use if :code:`authenticate_app` is True
            |default| :code:`None`
    :var bool auto_refresh_auth: If set to true, auto refresh the auth token once it expires. |default| :code:`True`
    :var Callable[[str,str],None] user_auth_refresh_callback: If set, gets called whenever a user auth token gets
        refreshed. Parameter: Auth Token, Refresh Token |default| :code:`None`
    :var Callable[[str,str],None] app_auth_refresh_callback: If set, gets called whenever a app auth token gets
        refreshed. Parameter: Auth Token |default| :code:`None`
    """
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    user_auth_refresh_callback: Optional[Callable[[str, str], None]] = None
    app_auth_refresh_callback: Optional[Callable[[str], None]] = None
    __app_auth_token: Optional[str] = None
    __app_auth_scope: List[AuthScope] = []
    __has_app_auth: bool = False

    __user_auth_token: Optional[str] = None
    __user_auth_refresh_token: Optional[str] = None
    __user_auth_scope: List[AuthScope] = []
    __has_user_auth: bool = False

    __logger: Logger = None

    auto_refresh_auth: bool = True

    def __init__(self,
                 app_id: str,
                 app_secret: Optional[str] = None,
                 authenticate_app: bool = True,
                 target_app_auth_scope: Optional[List[AuthScope]] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.__logger = getLogger('twitchAPI.twitch')
        if authenticate_app:
            self.authenticate_app(target_app_auth_scope if target_app_auth_scope is not None else [])

    def __generate_header(self, auth_type: 'AuthType', required_scope: List[AuthScope]) -> dict:
        header = {"Client-ID": self.app_id}
        if auth_type == AuthType.EITHER:
            has_auth, target, token, scope = self.__get_used_either_auth(required_scope)
            if not has_auth:
                raise UnauthorizedException('No authorization with correct scope set!')
            header['Authorization'] = f'Bearer {token}'
        elif auth_type == AuthType.APP:
            if not self.__has_app_auth:
                raise UnauthorizedException('Require app authentication!')
            for s in required_scope:
                if s not in self.__app_auth_scope:
                    raise MissingScopeException('Require app auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self.__app_auth_token}'
        elif auth_type == AuthType.USER:
            if not self.__has_user_auth:
                raise UnauthorizedException('require user authentication!')
            for s in required_scope:
                if s not in self.__user_auth_scope:
                    raise MissingScopeException('Require user auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self.__user_auth_token}'
        elif auth_type == AuthType.NONE:
            # set one anyway for better performance if possible but don't error if none found
            has_auth, target, token, scope = self.__get_used_either_auth(required_scope)
            if has_auth:
                header['Authorization'] = f'Bearer {token}'
        return header

    def __get_used_either_auth(self, required_scope: List[AuthScope]) -> \
            (bool, AuthType, Union[None, str], List[AuthScope]):
        if self.has_required_auth(AuthType.USER, required_scope):
            return True, AuthType.USER, self.__user_auth_token, self.__user_auth_scope
        if self.has_required_auth(AuthType.APP, required_scope):
            return True, AuthType.APP, self.__app_auth_token, self.__app_auth_scope
        return False, AuthType.NONE, None, []

    def get_user_auth_scope(self) -> List[AuthScope]:
        """Returns the set User auth Scope"""
        return self.__user_auth_scope

    def has_required_auth(self, required_type: AuthType, required_scope: List[AuthScope]) -> bool:
        if required_type == AuthType.NONE:
            return True
        if required_type == AuthType.EITHER:
            return self.has_required_auth(AuthType.USER, required_scope) or \
                   self.has_required_auth(AuthType.APP, required_scope)
        if required_type == AuthType.USER:
            if not self.__has_user_auth:
                return False
            for s in required_scope:
                if s not in self.__user_auth_scope:
                    return False
            return True
        if required_type == AuthType.APP:
            if not self.__has_app_auth:
                return False
            for s in required_scope:
                if s not in self.__app_auth_scope:
                    return False
            return True
        # default to false
        return False

    # FIXME rewrite refresh_used_token
    def refresh_used_token(self):
        """Refreshes the currently used token"""
        if self.__has_user_auth:
            self.__logger.debug('refreshing user token')
            from .oauth import refresh_access_token
            self.__user_auth_token, \
                self.__user_auth_refresh_token = refresh_access_token(self.__user_auth_refresh_token,
                                                                      self.app_id,
                                                                      self.app_secret)
            if self.user_auth_refresh_callback is not None:
                self.user_auth_refresh_callback(self.__user_auth_token, self.__user_auth_refresh_token)
        else:
            self.__generate_app_token()
            if self.app_auth_refresh_callback is not None:
                self.app_auth_refresh_callback(self.__app_auth_token)

    def __check_request_return(self,
                               response: requests.Response,
                               retry_func: Callable,
                               reply_func_has_data: bool,
                               url: str,
                               auth_type: 'AuthType',
                               required_scope: List[AuthScope],
                               data: Optional[dict] = None,
                               retries: int = 1
                               ) -> requests.Response:
        if self.auto_refresh_auth and retries > 0:
            if response.status_code == 401:
                # unauthorized, lets try to refresh the token once
                self.__logger.debug('got 401 response -> try to refresh token')
                self.refresh_used_token()
                if reply_func_has_data:
                    return retry_func(url, auth_type, required_scope, data=data, retries=retries - 1)
                else:
                    return retry_func(url, auth_type, required_scope, retries=retries - 1)
            elif response.status_code == 503:
                # service unavailable, retry exactly once as recommended by twitch documentation
                self.__logger.debug('got 503 response -> retry once')
                if reply_func_has_data:
                    return retry_func(url, auth_type, required_scope, data=data, retries=retries - 1)
                else:
                    return retry_func(url, auth_type, required_scope, retries=retries - 1)
        elif self.auto_refresh_auth and retries <= 0:
            if response.status_code == 503:
                raise TwitchBackendException('The Twitch API returns a server error')
            if response.status_code == 401:
                msg = response.json().get('message', '')
                self.__logger.debug(f'got 401 response and can\'t refresh. Message: "{msg}"')
                raise UnauthorizedException(msg)
        if response.status_code == 500:
            raise TwitchBackendException('Internal Server Error')
        if response.status_code == 400:
            raise TwitchAPIException('Bad Request')
        if str(response.headers['Ratelimit-Remaining']) == '0' or response.status_code == 429:
            self.__logger.warning('reached rate limit, waiting for reset')
            import time
            reset = int(response.headers['Ratelimit-Reset'])
            while int(time.time()) <= reset:
                time.sleep(0.01)
        return response

    def __api_post_request(self,
                           url: str,
                           auth_type: 'AuthType',
                           required_scope: List[AuthScope],
                           data: Optional[dict] = None,
                           retries: int = 1) -> requests.Response:
        """Make POST request with authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        self.__logger.debug(f'making POST request to {url}')
        if data is None:
            req = requests.post(url, headers=headers)
        else:
            req = requests.post(url, headers=headers, json=data)
        return self.__check_request_return(req,
                                           self.__api_post_request,
                                           True,
                                           url,
                                           auth_type,
                                           required_scope,
                                           data,
                                           retries)

    def __api_put_request(self,
                          url: str,
                          auth_type: 'AuthType',
                          required_scope: List[AuthScope],
                          data: Optional[dict] = None,
                          retries: int = 1) -> requests.Response:
        """Make PUT request with authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        self.__logger.debug(f'making PUT request to {url}')
        if data is None:
            req = requests.put(url, headers=headers)
        else:
            req = requests.put(url, headers=headers, json=data)
        return self.__check_request_return(req,
                                           self.__api_put_request,
                                           True,
                                           url,
                                           auth_type,
                                           required_scope,
                                           data,
                                           retries)

    def __api_patch_request(self,
                            url: str,
                            auth_type: 'AuthType',
                            required_scope: List[AuthScope],
                            data: Optional[dict] = None,
                            retries: int = 1) -> requests.Response:
        """Make PATCH request with authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        self.__logger.debug(f'making PATCH request to {url}')
        if data is None:
            req = requests.patch(url, headers=headers)
        else:
            req = requests.patch(url, headers=headers, json=data)
        return self.__check_request_return(req,
                                           self.__api_patch_request,
                                           True,
                                           url,
                                           auth_type,
                                           required_scope,
                                           data,
                                           retries)

    def __api_delete_request(self,
                             url: str,
                             auth_type: 'AuthType',
                             required_scope: List[AuthScope],
                             data: Optional[dict] = None,
                             retries: int = 1) -> requests.Response:
        """Make DELETE request with authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        self.__logger.debug(f'making DELETE request to {url}')
        if data is None:
            req = requests.delete(url, headers=headers)
        else:
            req = requests.delete(url, headers=headers, json=data)
        return self.__check_request_return(req,
                                           self.__api_delete_request,
                                           True,
                                           url,
                                           auth_type,
                                           required_scope,
                                           data,
                                           retries)

    def __api_get_request(self, url: str,
                          auth_type: 'AuthType',
                          required_scope: List[AuthScope],
                          retries: int = 1) -> requests.Response:
        """Make GET request with authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        self.__logger.debug(f'making GET request to {url}')
        req = requests.get(url, headers=headers)
        return self.__check_request_return(req,
                                           self.__api_get_request,
                                           False,
                                           url,
                                           auth_type,
                                           required_scope,
                                           None,
                                           retries)

    def __generate_app_token(self) -> None:
        if self.app_secret is None:
            raise MissingAppSecretException()
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'client_credentials',
            'scope': build_scope(self.__app_auth_scope)
        }
        self.__logger.debug('generating fresh app token')
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', params)
        result = requests.post(url)
        if result.status_code != 200:
            raise TwitchAuthorizationException(f'Authentication failed with code {result.status_code} ({result.text})')
        try:
            data = result.json()
            self.__app_auth_token = data['access_token']
        except ValueError:
            raise TwitchAuthorizationException('Authentication response did not have a valid json body')
        except KeyError:
            raise TwitchAuthorizationException('Authentication response did not contain access_token')

    def authenticate_app(self, scope: List[AuthScope]) -> None:
        """Authenticate with a fresh generated app token

        :param list[~twitchAPI.types.AuthScope] scope: List of Authorization scopes to use
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the authentication fails
        :return: None
        """
        self.__app_auth_scope = scope
        self.__generate_app_token()
        self.__has_app_auth = True

    def set_user_authentication(self,
                                token: str,
                                scope: List[AuthScope],
                                refresh_token: Optional[str] = None,
                                validate: bool = True):
        """Set a user token to be used.

        :param str token: the generated user token
        :param list[~twitchAPI.types.AuthScope] scope: List of Authorization Scopes that the given user token has
        :param str refresh_token: The generated refresh token, has to be provided if :attr:`auto_refresh_auth` is True
                    |default| :code:`None`
        :param bool validate: if true, validate the set token for being a user auth token and having the required scope
                    |default| :code:`True`
        :raises ValueError: if :attr:`auto_refresh_auth` is True but refresh_token is not set
        :raises ~twitchAPI.types.MissingScopeException: if given token is missing one of the required scopes
        :raises ~twitchAPI.types.InvalidTokenException: if the given token is invalid or for a different client id
        """
        if refresh_token is None and self.auto_refresh_auth:
            raise ValueError('refresh_token has to be provided when auto_refresh_user_auth is True')
        if validate:
            from .oauth import validate_token
            val_result = validate_token(token)
            if val_result.get('status', 200) == 401:
                raise InvalidTokenException(val_result.get('message', ''))
            if 'login' not in val_result or 'user_id' not in val_result:
                # this is a app token or not valid
                raise InvalidTokenException('not a user oauth token')
            if val_result.get('client_id') != self.app_id:
                raise InvalidTokenException('client id does not match')
            scopes = val_result.get('scopes', [])
            for s in scope:
                if s not in scopes:
                    raise MissingScopeException(f'given token is missing scope {s.value}')

        self.__user_auth_token = token
        self.__user_auth_refresh_token = refresh_token
        self.__user_auth_scope = scope
        self.__has_user_auth = True

    def get_app_token(self) -> Union[str, None]:
        """Returns the app token that the api uses or None when not authenticated.

        :return: app token
        :rtype: Union[str, None]
        """
        return self.__app_auth_token

    def get_user_auth_token(self) -> Union[str, None]:
        """Returns the current user auth token, None if no user Authentication is set

        :return: current user auth token
        :rtype: str or None
        """
        return self.__user_auth_token

    def get_used_token(self) -> Union[str, None]:
        """Returns the currently used token, can be either the app or user auth Token or None if no auth is set

        :return: the currently used auth token or None if no Authentication is set
        """
        # if no auth is set, self.__app_auth_token will be None
        return self.__user_auth_token if self.__has_user_auth else self.__app_auth_token

    # ======================================================================================================================
    # API calls
    # ======================================================================================================================

    def get_extension_analytics(self,
                                after: Optional[str] = None,
                                extension_id: Optional[str] = None,
                                first: int = 20,
                                ended_at: Optional[datetime] = None,
                                started_at: Optional[datetime] = None,
                                report_type: Optional[AnalyticsReportType] = None) -> dict:
        """Gets a URL that extension developers can use to download analytics reports (CSV files) for their extensions.
        The URL is valid for 5 minutes.\n\n

        Requires User authentication with scope :py:const:`twitchAPI.types.AuthScope.ANALYTICS_READ_EXTENSION`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-extension-analytics

        :param str after: cursor for forward pagination |default| :code:`None`
        :param str extension_id: If this is specified, the returned URL points to an analytics report for just the
                            specified extension. |default| :code:`None`
        :param int first: Maximum number of objects returned, range 1 to 100, |default| :code:`20`
        :param ~datetime.datetime ended_at: Ending date/time for returned reports, if this is provided,
                        `started_at` must also be specified. |default| :code:`None`
        :param ~datetime.datetime started_at: Starting date/time for returned reports, if this is provided,
                        `ended_at` must also be specified. |default| :code:`None`
        :param ~twitchAPI.types.AnalyticsReportType report_type: Type of analytics report that is returned
                        |default| :code:`None`
        :rtype: dict
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: When you only supply `started_at` or `ended_at` without the other or when first is not in
                        range 1 to 100
        """
        if ended_at is not None or started_at is not None:
            # you have to put in both:
            if ended_at is None or started_at is None:
                raise ValueError('you must specify both ended_at and started_at')
            if started_at > ended_at:
                raise ValueError('started_at must be before ended_at')
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        url_params = {
            'after': after,
            'ended_at': datetime_to_str(ended_at),
            'extension_id': extension_id,
            'first': first,
            'started_at': datetime_to_str(started_at),
            'type': enum_value_or_none(report_type)
        }
        url = build_url(TWITCH_API_BASE_URL + 'analytics/extensions',
                        url_params,
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, required_scope=[AuthScope.ANALYTICS_READ_EXTENSION])
        data = response.json()
        return make_fields_datetime(data, ['started_at', 'ended_at'])

    def get_game_analytics(self,
                           after: Optional[str] = None,
                           first: int = 20,
                           game_id: Optional[str] = None,
                           ended_at: Optional[datetime] = None,
                           started_at: Optional[datetime] = None,
                           report_type: Optional[AnalyticsReportType] = None) -> dict:
        """Gets a URL that game developers can use to download analytics reports (CSV files) for their games.
        The URL is valid for 5 minutes.\n\n

        Requires User authentication with scope :py:const:`twitchAPI.types.AuthScope.ANALYTICS_READ_GAMES`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-game-analytics

        :param str after: cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects returned, range 1 to 100, |default| :code:`20`
        :param str game_id: Game ID |default| :code:`None`
        :param ~datetime.datetime ended_at: Ending date/time for returned reports, if this is provided,
                        `started_at` must also be specified. |default| :code:`None`
        :param ~datetime.datetime started_at: Starting date/time for returned reports, if this is provided,
                        `ended_at` must also be specified. |default| :code:`None`
        :param ~twitchAPI.types.AnalyticsReportType report_type: Type of analytics report that is returned.
                        |default| :code:`None`
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: When you only supply `started_at` or `ended_at` without the other or when first is not in
                        range 1 to 100
        :rtype: dict
        """
        if ended_at is not None or started_at is not None:
            if ended_at is None or started_at is None:
                raise ValueError('you must specify both ended_at and started_at')
            if ended_at < started_at:
                raise ValueError('ended_at must be after started_at')
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        url_params = {
            'after': after,
            'ended_at': datetime_to_str(ended_at),
            'first': first,
            'game_id': game_id,
            'started_at': datetime_to_str(started_at),
            'type': enum_value_or_none(report_type)
        }
        url = build_url(TWITCH_API_BASE_URL + 'analytics/games',
                        url_params,
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, [AuthScope.ANALYTICS_READ_GAMES])
        data = response.json()
        return make_fields_datetime(data, ['ended_at', 'started_at'])

    def get_bits_leaderboard(self,
                             count: Optional[int] = 10,
                             period: Optional[TimePeriod] = TimePeriod.ALL,
                             started_at: Optional[datetime] = None,
                             user_id: Optional[str] = None) -> dict:
        """Gets a ranked list of Bits leaderboard information for an authorized broadcaster.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.BITS_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-bits-leaderboard

        :param int count: Number of results to be returned. In range 1 to 100, |default| :code:`10`
        :param ~twitchAPI.types.TimePeriod period: Time period over which data is aggregated, |default|
                :const:`twitchAPI.types.TimePeriod.ALL`
        :param ~datetime.datetime started_at: Timestamp for the period over which the returned data is aggregated.
                |default| :code:`None`
        :param str user_id: ID of the user whose results are returned; i.e., the person who paid for the Bits.
                |default| :code:`None`
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if count > 100 or count < 1:
            raise ValueError('count must be between 1 and 100')
        url_params = {
            'count': count,
            'period': period.value,
            'started_at': datetime_to_str(started_at),
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'bits/leaderboard', url_params, remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, [AuthScope.BITS_READ])
        data = response.json()
        return make_fields_datetime(data, ['ended_at', 'started_at'])

    def get_extension_transactions(self,
                                   extension_id: str,
                                   transaction_id: Optional[Union[str, List[str]]] = None,
                                   after: Optional[str] = None,
                                   first: int = 20) -> dict:
        """Get Extension Transactions allows extension back end servers to fetch a list of transactions that have
        occurred for their extension across all of Twitch.
        A transaction is a record of a user exchanging Bits for an in-Extension digital good.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-extension-transactions

        :param str extension_id: ID of the extension to list transactions for.
        :param union(list(str),str) transaction_id: Transaction IDs to look up. Can either be a list of str or str
                        |default| :code:`None`
        :param str after: cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects returned, range 1 to 100, |default| :code:`20`
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :raises ValueError: if transaction_ids is longer than 100 entries
        :rtype: dict
        """
        if first > 100 or first < 1:
            raise ValueError("first must be between 1 and 100")
        if transaction_id is not None and isinstance(transaction_id, list) and len(transaction_id) > 100:
            raise ValueError('transaction_ids cant be longer than 100 entries')
        url_param = {
            'extension_id': extension_id,
            'id': transaction_id,
            'after': after,
            first: first
        }
        url = build_url(TWITCH_API_BASE_URL + 'extensions/transactions', url_param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        data = result.json()
        return make_fields_datetime(data, ['timestamp'])

    def create_clip(self,
                    broadcaster_id: str,
                    has_delay: bool = False) -> dict:
        """Creates a clip programmatically. This returns both an ID and an edit URL for the new clip.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.CLIPS_EDIT`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-clip

        :param str broadcaster_id: Broadcaster ID of the stream from which the clip will be made.
        :param bool has_delay: If False, the clip is captured from the live stream when the API is called; otherwise,
                a delay is added before the clip is captured (to account for the brief delay between the broadcaster’s
                stream and the viewer’s experience of that stream). |default| :code:`False`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'has_delay': has_delay
        }
        url = build_url(TWITCH_API_BASE_URL + 'clips', param)
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CLIPS_EDIT])
        return result.json()

    def get_clips(self,
                  broadcaster_id: Optional[str] = None,
                  game_id: Optional[str] = None,
                  clip_id: Optional[List[str]] = None,
                  after: Optional[str] = None,
                  before: Optional[str] = None,
                  ended_at: Optional[datetime] = None,
                  started_at: Optional[datetime] = None,
                  first: int = 20) -> dict:
        """Gets clip information by clip ID (one or more), broadcaster ID (one only), or game ID (one only).
        Clips are returned sorted by view count, in descending order.\n\n

        Requires App or User authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-clips

        :param str broadcaster_id: ID of the broadcaster for whom clips are returned. |default| :code:`None`
        :param str game_id: ID of the game for which clips are returned. |default| :code:`None`
        :param list[str] clip_id: ID of the clip being queried. Limit: 100. |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param ~datetime.datetime ended_at: Ending date/time for returned clips |default| :code:`None`
        :param ~datetime.datetime started_at: Starting date/time for returned clips |default| :code:`None`
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if you try to query more than 100 clips in one call
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ValueError: if not exactly one of clip_id, broadcaster_id or game_id is given
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if clip_id is not None and len(clip_id) > 100:
            raise ValueError('A maximum of 100 clips can be queried in one call')
        if not (sum([clip_id is not None, broadcaster_id is not None, game_id is not None]) == 1):
            raise ValueError('You need to specify exactly one of clip_id, broadcaster_id or game_id')
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'game_id': game_id,
            'id': clip_id,
            'after': after,
            'before': before,
            'first': first,
            'ended_at': datetime_to_str(ended_at),
            'started_at': datetime_to_str(started_at)
        }
        url = build_url(TWITCH_API_BASE_URL + 'clips', param, split_lists=True, remove_none=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        data = result.json()
        return make_fields_datetime(data, ['created_at'])

    def get_code_status(self,
                        code: List[str],
                        user_id: int) -> dict:
        """Gets the status of one or more provided Bits codes.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-code-status

        :param list[str] code: The code to get the status of. Maximum of 20 entries
        :param int user_id: Represents the numeric Twitch user ID of the account which is going to receive the
                        entitlement associated with the code.
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if length of code is not in range 1 to 20
        :rtype: dict
        """
        if len(code) > 20 or len(code) < 1:
            raise ValueError('only between 1 and 20 codes are allowed')
        param = {
            'code': code,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'entitlements/codes', param, split_lists=True)
        result = self.__api_get_request(url, AuthType.APP, [])
        data = result.json()
        return fields_to_enum(data, ['status'], CodeStatus, CodeStatus.UNKNOWN_VALUE)

    def redeem_code(self,
                    code: List[str],
                    user_id: int) -> dict:
        """Redeems one or more provided Bits codes to the authenticated Twitch user.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#redeem-code

        :param list[str] code: The code to redeem to the authenticated user’s account. Maximum of 20 entries
        :param int user_id: Represents the numeric Twitch user ID of the account which  is going to receive the
                        entitlement associated with the code.
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if length of code is not in range 1 to 20
        :rtype: dict
        """
        if len(code) > 20 or len(code) < 1:
            raise ValueError('only between 1 and 20 codes are allowed')
        param = {
            'code': code,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'entitlements/code', param, split_lists=True)
        result = self.__api_post_request(url, AuthType.APP, [])
        data = result.json()
        return fields_to_enum(data, ['status'], CodeStatus, CodeStatus.UNKNOWN_VALUE)

    def get_top_games(self,
                      after: Optional[str] = None,
                      before: Optional[str] = None,
                      first: int = 20) -> dict:
        """Gets games sorted by number of current viewers on Twitch, most popular first.\n\n

        Requires App or User authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-top-games

        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        param = {
            'after': after,
            'before': before,
            'first': first
        }
        url = build_url(TWITCH_API_BASE_URL + 'games/top', param, remove_none=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def get_games(self,
                  game_ids: Optional[List[str]] = None,
                  names: Optional[List[str]] = None) -> dict:
        """Gets game information by game ID or name.\n\n

        Requires User or App authentication.
        In total, only 100 game ids and names can be fetched at once.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-games

        :param list[str] game_ids: Game ID |default| :code:`None`
        :param list[str] names: Game Name |default| :code:`None`
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if neither game_ids nor names are given or if game_ids and names are more than 100 entries
                        combined.
        :rtype: dict
        """
        if game_ids is None and names is None:
            raise ValueError('at least one of either game_ids and names has to be set')
        if (len(game_ids) if game_ids is not None else 0) + (len(names) if names is not None else 0) > 100:
            raise ValueError('in total, only 100 game_ids and names can be passed')
        param = {
            'id': game_ids,
            'name': names
        }
        url = build_url(TWITCH_API_BASE_URL + 'games', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def check_automod_status(self,
                             broadcaster_id: str,
                             automod_check_entries: List[AutoModCheckEntry]) -> dict:
        """Determines whether a string message meets the channel’s AutoMod requirements.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#check-automod-status

        :param str broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param list[~twitchAPI.types.AutoModCheckEntry] automod_check_entries: The Automod Check Entries
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'moderation/enforcements/status',
                        {'broadcaster_id': broadcaster_id})
        body = {'data': automod_check_entries}
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.MODERATION_READ], data=body)
        return result.json()

    def get_banned_events(self,
                          broadcaster_id: str,
                          user_id: Optional[str] = None,
                          after: Optional[str] = None,
                          first: int = 20) -> dict:
        """Returns all user bans and un-bans in a channel.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-banned-events

        :param str broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param str user_id: Filters the results and only returns a status object for users who are banned in
                        this channel and have a matching user_id |default| :code:`None`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 ot 100
        :rtype: dict
        """
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id,
            'after': after,
            'first': first
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/banned/events', param, remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.MODERATION_READ])
        data = result.json()
        data = fields_to_enum(data, ['event_type'], ModerationEventType, ModerationEventType.UNKNOWN)
        data = make_fields_datetime(data, ['event_timestamp', 'expires_at'])
        return data

    def get_banned_users(self,
                         broadcaster_id: str,
                         user_id: Optional[str] = None,
                         after: Optional[str] = None,
                         first: Optional[int] = 20,
                         before: Optional[str] = None) -> dict:
        """Returns all banned and timed-out users in a channel.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-banned-users

        :param str broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param str user_id: Filters the results and only returns a status object for users who are banned in this
                        channel and have a matching user_id. |default| :code:`None`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id,
            'after': after,
            'first': first,
            'before': before
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/banned', param, remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.MODERATION_READ])
        return make_fields_datetime(result.json(), ['expires_at'])

    def get_moderators(self,
                       broadcaster_id: str,
                       user_ids: Optional[List[str]] = None,
                       first: Optional[int] = 20,
                       after: Optional[str] = None) -> dict:
        """Returns all moderators in a channel.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-moderators

        :param str broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param list[str] user_ids: Filters the results and only returns a status object for users who are moderator in
                        this channel and have a matching user_id. Maximum 100 |default| :code:`None`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if user_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        if user_ids is not None and len(user_ids) > 100:
            raise ValueError('user_ids can only be 100 entries long')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'first': first,
            'after': after
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/moderators', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.MODERATION_READ])
        return result.json()

    def get_moderator_events(self,
                             broadcaster_id: str,
                             user_ids: Optional[List[str]] = None,
                             after: Optional[str] = None,
                             first: Optional[int] = 20) -> dict:
        """Returns a list of moderators or users added and removed as moderators from a channel.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-moderator-events

        :param str broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param list[str] user_ids: Filters the results and only returns a status object for users who are moderator in
                        this channel and have a matching user_id. Maximum 100 |default| :code:`None`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if user_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        if user_ids is not None and len(user_ids) > 100:
            raise ValueError('user_ids can only be 100 entries long')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'after': after,
            'first': first
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/moderators/events', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.MODERATION_READ])
        data = result.json()
        data = fields_to_enum(data, ['event_type'], ModerationEventType, ModerationEventType.UNKNOWN)
        data = make_fields_datetime(data, ['event_timestamp'])
        return data

    def create_stream_marker(self,
                             user_id: str,
                             description: Optional[str] = None) -> dict:
        """Creates a marker in the stream of a user specified by user ID.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-stream-marker

        :param str user_id: ID of the broadcaster in whose live stream the marker is created.
        :param str description: Description of or comments on the marker. Max length is 140 characters.
                        |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if description has more than 140 characters
        :rtype: dict
        """
        if description is not None and len(description) > 140:
            raise ValueError('max length for description is 140')
        url = build_url(TWITCH_API_BASE_URL + 'streams/markers', {})
        body = {'user_id': user_id}
        if description is not None:
            body['description'] = description
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_BROADCAST], data=body)
        data = result.json()
        return make_fields_datetime(data, ['created_at'])

    def get_streams(self,
                    after: Optional[str] = None,
                    before: Optional[str] = None,
                    first: int = 20,
                    game_id: Optional[List[str]] = None,
                    language: Optional[List[str]] = None,
                    user_id: Optional[List[str]] = None,
                    user_login: Optional[List[str]] = None) -> dict:
        """Gets information about active streams. Streams are returned sorted by number of current viewers, in
        descending order. Across multiple pages of results, there may be duplicate or missing streams, as viewers join
        and leave streams.\n\n

        Requires App or User authentication.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-streams

        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :param list[str] game_id: Returns streams broadcasting a specified game ID. You can specify up to 100 IDs.
                        |default| :code:`None`
        :param list[str] language: Stream language. You can specify up to 100 languages. |default| :code:`None`
        :param list[str] user_id: Returns streams broadcast by one or more specified user IDs. You can specify up
                        to 100 IDs. |default| :code:`None`
        :param list[str] user_login: Returns streams broadcast by one or more specified user login names.
                        You can specify up to 100 names. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or one of the following fields have more than 100 entries:
                        `user_id, game_id, language, user_login`
        :rtype: dict
        """
        if user_id is not None and len(user_id) > 100:
            raise ValueError('a maximum of 100 user_id entries are allowed')
        if user_login is not None and len(user_login) > 100:
            raise ValueError('a maximum of 100 user_login entries are allowed')
        if language is not None and len(language) > 100:
            raise ValueError('a maximum of 100 languages are allowed')
        if game_id is not None and len(game_id) > 100:
            raise ValueError('a maximum of 100 game_id entries are allowed')
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        param = {
            'after': after,
            'before': before,
            'first': first,
            'game_id': game_id,
            'language': language,
            'user_id': user_id,
            'user_login': user_login
        }
        url = build_url(TWITCH_API_BASE_URL + 'streams', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        data = result.json()
        return make_fields_datetime(data, ['started_at'])

    def get_stream_markers(self,
                           user_id: str,
                           video_id: str,
                           after: Optional[str] = None,
                           before: Optional[str] = None,
                           first: int = 20) -> dict:
        """Gets a list of markers for either a specified user’s most recent stream or a specified VOD/video (stream),
        ordered by recency.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-stream-markers

        Only one of user_id and video_id must be specified.

        :param str user_id: ID of the broadcaster from whose stream markers are returned.
        :param str video_id: ID of the VOD/video whose stream markers are returned.
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param int first: Number of values to be returned when getting videos by user or game ID. Limit: 100.
                        |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or neither user_id nor video_id is provided
        :rtype: dict
        """
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        if user_id is None and video_id is None:
            raise ValueError('you must specify either user_id and/or video_id')
        param = {
            'user_id': user_id,
            'video_id': video_id,
            'after': after,
            'before': before,
            'first': first
        }
        url = build_url(TWITCH_API_BASE_URL + 'streams/markers', param, remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.USER_READ_BROADCAST])
        return make_fields_datetime(result.json(), ['created_at'])

    def get_broadcaster_subscriptions(self,
                                      broadcaster_id: str,
                                      user_ids: Optional[List[str]] = None,
                                      after: Optional[str] = None,
                                      first: Optional[int] = 20) -> dict:
        """Get all of a broadcaster’s subscriptions.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-broadcaster-subscriptions

        :param str broadcaster_id: User ID of the broadcaster. Must match the User ID in the Bearer token.
        :param list[str] user_ids: Unique identifier of account to get subscription status of. Maximum 100 entries
                        |default| :code:`None`
        :param str after: Cursor for forward pagination. |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if user_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        if user_ids is not None and len(user_ids) > 100:
            raise ValueError('user_ids can have a maximum of 100 entries')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'first': first,
            'after': after
        }
        url = build_url(TWITCH_API_BASE_URL + 'subscriptions', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS])
        return result.json()

    def check_user_subscription(self,
                                broadcaster_id: str,
                                user_id: str) -> dict:
        """Checks if a specific user (user_id) is subscribed to a specific channel (broadcaster_id).

        Requires User or App Authorization with scope :const:`twitchAPI.types.AuthScope.USER_READ_SUBSCRIPTIONS`

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#check-user-subscription

        :param str broadcaster_id: User ID of an Affiliate or Partner broadcaster.
        :param str user_id: User ID of a Twitch viewer.
        :rtype: dict
        :raises ~twitchAPI.types.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the app or user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'subscriptions/user', param)
        result = self.__api_get_request(url, AuthType.EITHER, [AuthScope.USER_READ_SUBSCRIPTIONS])
        return result.json()

    def get_all_stream_tags(self,
                            after: Optional[str] = None,
                            first: int = 20,
                            tag_ids: Optional[List[str]] = None) -> dict:
        """Gets the list of all stream tags defined by Twitch, optionally filtered by tag ID(s).\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-all-stream-tags

        :param str after: Cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :param list[str] tag_ids: IDs of tags. Maximum 100 entries |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or tag_ids has more than 100 entries
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        if tag_ids is not None and len(tag_ids) > 100:
            raise ValueError('tag_ids can not have more than 100 entries')
        param = {
            'after': after,
            'first': first,
            'tag_id': tag_ids
        }
        url = build_url(TWITCH_API_BASE_URL + 'tags/streams', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.APP, [])
        return result.json()

    def get_stream_tags(self,
                        broadcaster_id: str) -> dict:
        """Gets the list of tags for a specified stream (channel).\n\n

        Requires User authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-stream-tags

        :param str broadcaster_id: ID of the stream that's tags are going to be fetched
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'streams/tags', {'broadcaster_id': broadcaster_id})
        result = self.__api_get_request(url, AuthType.USER, [])
        return result.json()

    def replace_stream_tags(self,
                            broadcaster_id: str,
                            tag_ids: List[str]) -> dict:
        """Applies specified tags to a specified stream, overwriting any existing tags applied to that stream.
        If no tags are specified, all tags previously applied to the stream are removed.
        Automated tags are not affected by this operation.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#replace-stream-tags

        :param str broadcaster_id: ID of the stream for which tags are to be replaced.
        :param list[str] tag_ids: IDs of tags to be applied to the stream. Maximum of 100 supported.
        :return: {}
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if more than 100 tag_ids where provided
        :rtype: dict
        """
        if len(tag_ids) > 100:
            raise ValueError('tag_ids can not have more than 100 entries')
        url = build_url(TWITCH_API_BASE_URL + 'streams/tags', {'broadcaster_id': broadcaster_id})
        self.__api_put_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_BROADCAST], data={'tag_ids': tag_ids})
        # this returns nothing
        return {}

    def get_channel_teams(self,
                          broadcaster_id: str) -> dict:
        """Retrieves a list of Twitch Teams of which the specified channel/broadcaster is a member.\n\n

        Requires User or App authentication.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference/#get-channel-teams

        :param str broadcaster_id: User ID for a Twitch user.
        :rtype: dict
        :raises ~twitchAPI.types.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        """
        url = build_url(TWITCH_API_BASE_URL + 'teams/channel', {'broadcaster_id': broadcaster_id})
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return make_fields_datetime(result.json(), ['created_at', 'updated_at'])

    def get_teams(self,
                  team_id: Optional[str] = None,
                  name: Optional[str] = None) -> dict:
        """Gets information for a specific Twitch Team.\n\n

        Requires User or App authentication.
        One of the two optional query parameters must be specified.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference/#get-teams

        :param str team_id: Team ID |default| :code:`None`
        :param str name: Team Name |default| :code:`None`
        :raises ~twitchAPI.types.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if neither team_id nor name are given or if both team_id and names are given.
        :rtype: dict
        """
        if team_id is None and name is None:
            raise ValueError('You need to specify one of the two optional parameter.')
        if team_id is not None and name is not None:
            raise ValueError('Only one optional parameter must be specified.')
        param = {
            'id': team_id,
            'name': name
        }
        url = build_url(TWITCH_API_BASE_URL + 'teams', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return make_fields_datetime(result.json(), ['created_at', 'updated_at'])

    def get_users(self,
                  user_ids: Optional[List[str]] = None,
                  logins: Optional[List[str]] = None) -> dict:
        """Gets information about one or more specified Twitch users.
        Users are identified by optional user IDs and/or login name.
        If neither a user ID nor a login name is specified, the user is the one authenticated.\n\n

        Requires App authentication if either user_ids or logins is provided, otherwise requires a User authentication.
        If you have user Authentication and want to get your email info, you also need the authentication scope
        :const:`twitchAPI.types.AuthScope.USER_READ_EMAIL`\n
        If you provide user_ids and/or logins, the maximum combined entries should not exceed 100.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-users

        :param list[str] user_ids: User ID. Multiple user IDs can be specified. Limit: 100. |default| :code:`None`
        :param list[str] logins: User login name. Multiple login names can be specified. Limit: 100.
                        |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if more than 100 combined user_ids and logins where provided
        :rtype: dict
        """
        if (len(user_ids) if user_ids is not None else 0) + (len(logins) if logins is not None else 0) > 100:
            raise ValueError('the total number of entries in user_ids and logins can not be more than 100')
        url_params = {
            'id': user_ids,
            'login': logins
        }
        url = build_url(TWITCH_API_BASE_URL + 'users', url_params, remove_none=True, split_lists=True)
        response = self.__api_get_request(url,
                                          AuthType.USER if (user_ids is None or len(user_ids) == 0) and (
                                                      logins is None or len(logins) == 0) else AuthType.EITHER,
                                          [])
        return response.json()

    def get_users_follows(self,
                          after: Optional[str] = None,
                          first: int = 20,
                          from_id: Optional[str] = None,
                          to_id: Optional[str] = None) -> dict:
        """Gets information on follow relationships between two Twitch users.
        Information returned is sorted in order, most recent follow first.\n\n

        Requires App authentication.\n
        You have to use at least one of the following fields: from_id, to_id
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-users-follows

        :param str after: Cursor for forward pagination |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :param str from_id: User ID. The request returns information about users who are being followed by
                        the from_id user. |default| :code:`None`
        :param str to_id: User ID. The request returns information about users who are following the to_id user.
                        |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or neither from_id nor to_id is provided
        :rtype: dict
        """
        if first > 100 or first < 1:
            raise ValueError('first must be between 1 and 100')
        if from_id is None and to_id is None:
            raise ValueError('at least one of from_id and to_id needs to be set')
        param = {
            'after': after,
            'first': first,
            'from_id': from_id,
            'to_id': to_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'users/follows', param, remove_none=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return make_fields_datetime(result.json(), ['followed_at'])

    def update_user(self,
                    description: str) -> dict:
        """Updates the description of the Authenticated user.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.USER_EDIT`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-user

        :param str description: User’s account description
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'users', {'description': description})
        result = self.__api_put_request(url, AuthType.USER, [AuthScope.USER_EDIT])
        return result.json()

    def get_user_extensions(self) -> dict:
        """Gets a list of all extensions (both active and inactive) for the authenticated user\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-extensions

        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'users/extensions/list', {})
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.USER_READ_BROADCAST])
        return result.json()

    def get_user_active_extensions(self,
                                   user_id: Optional[str] = None) -> dict:
        """Gets information about active extensions installed by a specified user, identified by a user ID or the
        authenticated user.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-active-extensions

        :param str user_id: ID of the user whose installed extensions will be returned. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'users/extensions', {'user_id': user_id}, remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.USER_READ_BROADCAST])
        return result.json()

    def update_user_extensions(self,
                               data: dict) -> dict:
        """"Updates the activation state, extension ID, and/or version number of installed extensions
        for the authenticated user.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.USER_EDIT_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-user-extensions

        :param dict data: The user extension data to be written
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'users/extensions', {})
        result = self.__api_put_request(url,
                                        AuthType.USER,
                                        [AuthScope.USER_EDIT_BROADCAST],
                                        data=data)
        return result.json()

    def get_videos(self,
                   ids: Optional[List[str]] = None,
                   user_id: Optional[str] = None,
                   game_id: Optional[str] = None,
                   after: Optional[str] = None,
                   before: Optional[str] = None,
                   first: Optional[int] = 20,
                   language: Optional[str] = None,
                   period: TimePeriod = TimePeriod.ALL,
                   sort: SortMethod = SortMethod.TIME,
                   video_type: VideoType = VideoType.ALL) -> dict:
        """Gets video information by video ID (one or more), user ID (one only), or game ID (one only).\n\n

        Requires App authentication.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-videos

        :param list[str] ids: ID of the video being queried. Limit: 100. |default| :code:`None`
        :param str user_id: ID of the user who owns the video. |default| :code:`None`
        :param str game_id: ID of the game the video is of. |default| :code:`None`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param str before: Cursor for backward pagination |default| :code:`None`
        :param int first: Number of values to be returned when getting videos by user or game ID.
                        Limit: 100. |default| :code:`20`
        :param str language: Language of the video being queried. |default| :code:`None`
        :param ~twitchAPI.types.TimePeriod period: Period during which the video was created.
                        |default| :code:`TimePeriod.ALL`
        :param ~twitchAPI.types.SortMethod sort: Sort order of the videos.
                        |default| :code:`SortMethod.TIME`
        :param ~twitchAPI.types.VideoType video_type: Type of video.
                        |default| :code:`VideoType.ALL`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100, ids has more than 100 entries or none of ids, user_id
                        nor game_id is provided.
        :rtype: dict
        """
        if ids is None and user_id is None and game_id is None:
            raise ValueError('you must use either ids, user_id or game_id')
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        if ids is not None and len(ids) > 100:
            raise ValueError('ids can only have a maximum of 100 entries')
        param = {
            'id': ids,
            'user_id': user_id,
            'game_id': game_id,
            'after': after,
            'before': before,
            'first': first,
            'language': language,
            'period': period.value,
            'sort': sort.value,
            'type': video_type.value
        }
        url = build_url(TWITCH_API_BASE_URL + 'videos', param, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        data = result.json()
        data = make_fields_datetime(data, ['created_at', 'published_at'])
        data = fields_to_enum(data, ['type'], VideoType, VideoType.UNKNOWN)
        return data

    def get_webhook_subscriptions(self,
                                  first: Optional[int] = 20,
                                  after: Optional[str] = None) -> dict:
        """Gets the Webhook subscriptions of the authenticated user, in order of expiration.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-webhook-subscriptions

        :param int first: Number of values to be returned per page. Limit: 100. |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        url = build_url(TWITCH_API_BASE_URL + 'webhooks/subscriptions',
                        {'first': first, 'after': after},
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.APP, [])
        return response.json()

    def get_channel_information(self,
                                broadcaster_id: str) -> dict:
        """Gets channel information for users.\n\n

        Requires App or user authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-information

        :param str broadcaster_id: ID of the channel to be updated
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'channels', {'broadcaster_id': broadcaster_id})
        response = self.__api_get_request(url, AuthType.EITHER, [])
        return response.json()

    def modify_channel_information(self,
                                   broadcaster_id: str,
                                   game_id: Optional[str] = None,
                                   broadcaster_language: Optional[str] = None,
                                   title: Optional[str] = None,
                                   delay: Optional[int] = None) -> bool:
        """Modifies channel information for users.\n\n

        Requires User authentication with scope :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#modify-channel-information

        :param str broadcaster_id: ID of the channel to be updated
        :param str game_id: The current game ID being played on the channel |default| :code:`None`
        :param str broadcaster_language: The language of the channel |default| :code:`None`
        :param str title: The title of the stream |default| :code:`None`
        :param int delay: Stream delay in seconds. Trying to set this while not being a Twitch Partner will fail!
                        |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if none of the following fields are specified: `game_id, broadcaster_language, title`
        :raises ValueError: if title is a empty string
        :rtype: bool
        """
        if game_id is None and broadcaster_language is None and title is None:
            raise ValueError('You need to specify at least one of the optional parameter')
        if len(title) == 0:
            raise ValueError('title cant be a empty string')
        url = build_url(TWITCH_API_BASE_URL + 'channels',
                        {'broadcaster_id': broadcaster_id}, remove_none=True)
        body = {k: v for k, v in {'game_id': game_id,
                                  'broadcaster_language': broadcaster_language,
                                  'title': title,
                                  'delay': delay}.items() if v is not None}
        response = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_BROADCAST], data=body)
        return response.status_code == 204

    def search_channels(self,
                        query: str,
                        first: Optional[int] = 20,
                        after: Optional[str] = None,
                        live_only: Optional[bool] = False) -> dict:
        """Returns a list of channels (users who have streamed within the past 6 months) that match the query via
        channel name or description either entirely or partially.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#search-channels

        :param str query: search query
        :param int first: Maximum number of objects to return. Maximum: 100 |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :param bool live_only: Filter results for live streams only. |default| :code:`False`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        url = build_url(TWITCH_API_BASE_URL + 'search/channels',
                        {'query': query,
                         'first': first,
                         'after': after,
                         'live_only': live_only}, remove_none=True)
        response = self.__api_get_request(url, AuthType.EITHER, [])
        return make_fields_datetime(response.json(), ['started_at'])

    def search_categories(self,
                          query: str,
                          first: Optional[int] = 20,
                          after: Optional[str] = None) -> dict:
        """Returns a list of games or categories that match the query via name either entirely or partially.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#search-categories

        :param str query: search query
        :param int first: Maximum number of objects to return. Maximum: 100 |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        url = build_url(TWITCH_API_BASE_URL + 'search/categories',
                        {'query': query,
                         'first': first,
                         'after': after}, remove_none=True)
        response = self.__api_get_request(url, AuthType.EITHER, [])
        return response.json()

    def get_stream_key(self,
                       broadcaster_id: str) -> dict:
        """Gets the channel stream key for a user.\n\n

        Requires User authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_STREAM_KEY`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-stream-key

        :param str broadcaster_id: User ID of the broadcaster
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'streams/key', {'broadcaster_id': broadcaster_id})
        response = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_STREAM_KEY])
        return response.json()

    def start_commercial(self,
                         broadcaster_id: str,
                         length: int) -> dict:
        """Starts a commercial on a specified channel.\n\n

        Requires User authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_EDIT_COMMERCIAL`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#start-commercial

        :param str broadcaster_id: ID of the channel requesting a commercial
        :param int length: Desired length of the commercial in seconds. , one of these: [30, 60, 90, 120, 150, 180]
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if length is not one of these: :code:`30, 60, 90, 120, 150, 180`
        :rtype: dict
        """
        if length not in [30, 60, 90, 120, 150, 180]:
            raise ValueError('length needs to be one of these: [30, 60, 90, 120, 150, 180]')
        url = build_url(TWITCH_API_BASE_URL + 'channels/commercial',
                        {'broadcaster_id': broadcaster_id,
                         'length': length})
        response = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_EDIT_COMMERCIAL])
        return response.json()

    def get_cheermotes(self,
                       broadcaster_id: str) -> dict:
        """Retrieves the list of available Cheermotes, animated emotes to which viewers can assign Bits,
        to cheer in chat.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-cheermotes

        :param str broadcaster_id: ID for the broadcaster who might own specialized Cheermotes.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'bits/cheermotes',
                        {'broadcaster_id': broadcaster_id})
        response = self.__api_get_request(url, AuthType.EITHER, [])
        return make_fields_datetime(response.json(), ['last_updated'])

    def get_hype_train_events(self,
                              broadcaster_id: str,
                              first: Optional[int] = 1,
                              id: Optional[str] = None,
                              cursor: Optional[str] = None) -> dict:
        """Gets the information of the most recent Hype Train of the given channel ID.
        When there is currently an active Hype Train, it returns information about that Hype Train.
        When there is currently no active Hype Train, it returns information about the most recent Hype Train.
        After 5 days, if no Hype Train has been active, the endpoint will return an empty response.\n\n

        Requires App or User authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-hype-train-events

        :param str broadcaster_id: User ID of the broadcaster.
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`1`
        :param str id: The id of the wanted event, if known |default| :code:`None`
        :param str cursor: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        url = build_url(TWITCH_API_BASE_URL + 'hypetrain/events',
                        {'broadcaster_id': broadcaster_id,
                         'first': first,
                         'id': id,
                         'cursor': cursor}, remove_none=True)
        response = self.__api_get_request(url, AuthType.EITHER, [AuthScope.CHANNEL_READ_HYPE_TRAIN])
        data = make_fields_datetime(response.json(), ['event_timestamp',
                                                      'started_at',
                                                      'expires_at',
                                                      'cooldown_end_time'])
        data = fields_to_enum(data, ['type'], HypeTrainContributionMethod, HypeTrainContributionMethod.UNKNOWN)
        return data

    def get_drops_entitlements(self,
                               id: Optional[str] = None,
                               user_id: Optional[str] = None,
                               game_id: Optional[str] = None,
                               after: Optional[str] = None,
                               first: Optional[int] = 20) -> dict:
        """Gets a list of entitlements for a given organization that have been granted to a game, user, or both.

        OAuth Token Client ID must have ownership of Game\n\n

        Requires App or User authentication\n
        See Twitch documentation for valid parameter combinations!\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-drops-entitlements

        :param str id: Unique Identifier of the entitlement |default| :code:`None`
        :param str user_id: A Twitch User ID |default| :code:`None`
        :param str game_id: A Twitch Game ID |default| :code:`None`
        :param str after: The cursor used to fetch the next page of data. |default| :code:`None`
        :param int first: Maximum number of entitlements to return. Maximum: 100 |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 1000
        :rtype: dict
        """
        if first < 1 or first > 1000:
            raise ValueError('first must be between 1 and 1000')
        can_use, auth_type, token, scope = self.__get_used_either_auth([])
        if auth_type == AuthType.USER:
            if user_id is not None:
                raise ValueError('cant use user_id when using User Authentication')
        url = build_url(TWITCH_API_BASE_URL + 'entitlements/drops',
                        {
                            'id': id,
                            'user_id': user_id,
                            'game_id': game_id,
                            'after': after,
                            'first': first
                        }, remove_none=True)
        response = self.__api_get_request(url, AuthType.EITHER, [])
        data = make_fields_datetime(response.json(), ['timestamp'])
        return data

    def create_custom_reward(self,
                             broadcaster_id: str,
                             title: str,
                             cost: int,
                             prompt: Optional[str] = None,
                             is_enabled: Optional[bool] = True,
                             background_color: Optional[str] = None,
                             is_user_input_required: Optional[bool] = False,
                             is_max_per_stream_enabled: Optional[bool] = False,
                             max_per_stream: Optional[int] = None,
                             is_max_per_user_per_stream_enabled: Optional[bool] = False,
                             max_per_user_per_stream: Optional[int] = None,
                             is_global_cooldown_enabled: Optional[bool] = False,
                             global_cooldown_seconds: Optional[int] = None,
                             should_redemptions_skip_request_queue: Optional[bool] = False) -> dict:
        """Creates a Custom Reward on a channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-custom-rewards

        :param str broadcaster_id: ID of the broadcaster, must be same as user_id of auth token
        :param str title: The title of the reward
        :param int cost: The cost of the reward
        :param str prompt: The prompt for the viewer when they are redeeming the reward |default| :code:`None`
        :param is_enabled: Is the reward currently enabled, if false the reward won’t show up to viewers.
                    |default| :code:`True`
        :param str background_color: Custom background color for the reward.
                    Format: Hex with # prefix. Example: :code:`#00E5CB`. |default| :code:`None`
        :param bool is_user_input_required: Does the user need to enter information when redeeming the reward.
                    |default| :code:`False`
        :param bool is_max_per_stream_enabled: Whether a maximum per stream is enabled. |default| :code:`False`
        :param int max_per_stream: The maximum number per stream if enabled |default| :code:`None`
        :param bool is_max_per_user_per_stream_enabled: Whether a maximum per user per stream is enabled.
                    |default| :code:`False`
        :param int max_per_user_per_stream: The maximum number per user per stream if enabled |default| :code:`None`
        :param bool is_global_cooldown_enabled: Whether a cooldown is enabled. |default| :code:`False`
        :param int global_cooldown_seconds: The cooldown in seconds if enabled |default| :code:`None`
        :param bool should_redemptions_skip_request_queue: Should redemptions be set to FULFILLED status immediately
                    when redeemed and skip the request queue instead of the normal UNFULFILLED status.
                    |default| :code:`False`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ValueError: if is_global_cooldown_enabled is True but global_cooldown_seconds is not specified
        :raises ValueError: if is_max_per_stream_enabled is True but max_per_stream is not specified
        :raises ValueError: if is_max_per_user_per_stream_enabled is True but max_per_user_per_stream is not specified
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if Channel Points are not available for the broadcaster
        :rtype: dict
        """

        if is_global_cooldown_enabled and global_cooldown_seconds is None:
            raise ValueError('please specify global_cooldown_seconds')
        if is_max_per_stream_enabled and max_per_stream is None:
            raise ValueError('please specify max_per_stream')
        if is_max_per_user_per_stream_enabled and max_per_user_per_stream is None:
            raise ValueError('please specify max_per_user_per_stream')

        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards',
                        {'broadcaster_id': broadcaster_id})
        body = {x: y for x, y in {
            'title': title,
            'prompt': prompt,
            'cost': cost,
            'is_enabled': is_enabled,
            'background_color': background_color,
            'is_user_input_required': is_user_input_required,
            'is_max_per_stream_enabled': is_max_per_stream_enabled,
            'max_per_stream': max_per_stream,
            'is_max_per_user_per_stream_enabled': is_max_per_user_per_stream_enabled,
            'max_per_user_per_stream': max_per_user_per_stream,
            'is_global_cooldown_enabled': is_global_cooldown_enabled,
            'global_cooldown_seconds': global_cooldown_seconds,
            'should_redemptions_skip_request_queue': should_redemptions_skip_request_queue
        }.items() if y is not None}
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS], body)
        if result.status_code == 403:
            raise TwitchAPIException('Forbidden: Channel Points are not available for the broadcaster')
        data = result.json()
        return make_fields_datetime(data, ['cooldown_expires_at'])

    def delete_custom_reward(self,
                             broadcaster_id: str,
                             reward_id: str):
        """Deletes a Custom Reward on a channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-custom-rewards

        :param str broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param str reward_id: ID of the Custom Reward to delete, must match a Custom Reward on broadcaster_id’s channel.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.types.NotFoundException: if the broadcaster has no custom reward with the given id
        """

        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards',
                        {'broadcaster_id': broadcaster_id,
                         'id': reward_id})
        result = self.__api_delete_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS])

        if result.status_code == 200:
            return
        if result.status_code == 404:
            raise NotFoundException()

    def get_custom_reward(self,
                          broadcaster_id: str,
                          reward_id: Optional[Union[str,List[str]]] = None,
                          only_manageable_rewards: Optional[bool] = False) -> dict:
        """Returns a list of Custom Reward objects for the Custom Rewards on a channel.
        Developers only have access to update and delete rewards that the same/calling client_id created.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-custom-reward

        :param str broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param union[list[str],str] reward_id: When used, this parameter filters the results and only returns reward
                objects for the Custom Rewards with matching ID. Maximum: 50
                Can be either a list of str or str |default| :code:`None`
        :param bool only_manageable_rewards: When set to true, only returns custom rewards
                that the calling client_id can manage. |default| :code:`false`
        :rtype: dict
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if if reward_id is longer than 50 entries
        """

        if reward_id is not None and isinstance(reward_id, list) and len(reward_id) > 50:
            raise ValueError('reward_id can not contain more than 50 entries')
        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': reward_id,
                            'only_manageable_rewards': only_manageable_rewards
                        }, remove_none=True, split_lists=True)

        result = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_REDEMPTIONS])
        return make_fields_datetime(result.json(), ['cooldown_expires_at'])

    def get_custom_reward_redemption(self,
                                     broadcaster_id: str,
                                     reward_id: str,
                                     id: Optional[List[str]] = None,
                                     status: Optional[CustomRewardRedemptionStatus] = None,
                                     sort: Optional[SortOrder] = SortOrder.OLDEST,
                                     after: Optional[str] = None,
                                     first: Optional[int] = 20) -> dict:
        """Returns Custom Reward Redemption objects for a Custom Reward on a channel that was created by the
        same client_id.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-custom-reward-redemption

        :param str broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param str reward_id: When ID is not provided, this parameter returns paginated Custom
                Reward Redemption objects for redemptions of the Custom Reward with ID reward_id
        :param list(str) id: When used, this param filters the results and only returns |default| :code:`None`
                Custom Reward Redemption objects for the redemptions with matching ID. Maximum: 50 ids
                |default| :code:`None`
        :param ~twitchAPI.types.CustomRewardRedemptionStatus status: When id is not provided, this param is required
                and filters the paginated Custom Reward Redemption objects for redemptions with the matching status.
                |default| :code:`None`
        :param ~twitchAPI.types.SortOrder sort: Sort order of redemptions returned when getting the paginated
                Custom Reward Redemption objects for a reward.
                |default| :code:`SortOrder.OLDEST`
        :param str after: Cursor for forward pagination. |default| :code:`None`
        :param int first: Number of results to be returned when getting the paginated Custom Reward
                Redemption objects for a reward. Limit: 50
                |default| :code:`20`
        :rtype: dict
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if id has more than 50 entries
        :raises ValueError: if first is not in range 1 to 50
        :raises ValueError: if status and id are both :code:`None`
        """

        if first is not None and (first < 1 or first > 50):
            raise ValueError('first must be in range 1 to 50')
        if id is not None and len(id) > 50:
            raise ValueError('id can not have more than 50 entries')
        if status is None and id is None:
            raise ValueError('you have to set at least one of status or id')

        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards/redemptions',
                        {
                            'broadcaster_id': broadcaster_id,
                            'reward_id': reward_id,
                            'id': id,
                            'status': status,
                            'sort': sort,
                            'after': after,
                            'first': first
                        }, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_REDEMPTIONS])
        data = make_fields_datetime(result.json(), ['redeemed_at'])
        data = fields_to_enum(data,
                              ['status'],
                              CustomRewardRedemptionStatus,
                              CustomRewardRedemptionStatus.CANCELED)
        return data

    def update_custom_reward(self,
                             broadcaster_id: str,
                             reward_id: str,
                             title: Optional[str] = None,
                             prompt: Optional[str] = None,
                             cost: Optional[int] = None,
                             is_enabled: Optional[bool] = True,
                             background_color: Optional[str] = None,
                             is_user_input_required: Optional[bool] = False,
                             is_max_per_stream_enabled: Optional[bool] = False,
                             max_per_stream: Optional[int] = None,
                             is_max_per_user_per_stream_enabled: Optional[bool] = False,
                             max_per_user_per_stream: Optional[int] = None,
                             is_global_cooldown_enabled: Optional[bool] = False,
                             global_cooldown_seconds: Optional[int] = None,
                             should_redemptions_skip_request_queue: Optional[bool] = False) -> dict:
        """Updates a Custom Reward created on a channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-custom-rewards

        :param str broadcaster_id: ID of the broadcaster, must be same as user_id of auth token
        :param str reward_id: ID of the reward that you want to update
        :param str title: The title of the reward |default| :code:`None`
        :param str prompt: The prompt for the viewer when they are redeeming the reward |default| :code:`None`
        :param int cost: The cost of the reward |default| :code:`None`
        :param is_enabled: Is the reward currently enabled, if false the reward won’t show up to viewers.
                    |default| :code:`true`
        :param str background_color: Custom background color for the reward. |default| :code:`None`
                    Format: Hex with # prefix. Example: :code:`#00E5CB`.
        :param bool is_user_input_required: Does the user need to enter information when redeeming the reward.
                    |default| :code:`false`
        :param bool is_max_per_stream_enabled: Whether a maximum per stream is enabled. |default| :code:`false`
        :param int max_per_stream: The maximum number per stream if enabled |default| :code:`None`
        :param bool is_max_per_user_per_stream_enabled: Whether a maximum per user per stream is enabled.
                    |default| :code:`false`
        :param int max_per_user_per_stream: The maximum number per user per stream if enabled |default| :code:`None`
        :param bool is_global_cooldown_enabled: Whether a cooldown is enabled. |default| :code:`false`
        :param int global_cooldown_seconds: The cooldown in seconds if enabled |default| :code:`None`
        :param bool should_redemptions_skip_request_queue: Should redemptions be set to FULFILLED status immediately
                    when redeemed and skip the request queue instead of the normal UNFULFILLED status.
                    |default| :code:`false`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ValueError: if is_global_cooldown_enabled is True but global_cooldown_seconds is not specified
        :raises ValueError: if is_max_per_stream_enabled is True but max_per_stream is not specified
        :raises ValueError: if is_max_per_user_per_stream_enabled is True but max_per_user_per_stream is not specified
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        :raises ValueError: if the given reward_id does not match a custom reward by the given broadcaster
        :rtype: dict
        """

        if is_global_cooldown_enabled and global_cooldown_seconds is None:
            raise ValueError('please specify global_cooldown_seconds')
        if is_max_per_stream_enabled and max_per_stream is None:
            raise ValueError('please specify max_per_stream')
        if is_max_per_user_per_stream_enabled and max_per_user_per_stream is None:
            raise ValueError('please specify max_per_user_per_stream')

        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards',
                        {'broadcaster_id': broadcaster_id,
                         'id': reward_id})
        body = {x: y for x, y in {
            'title': title,
            'prompt': prompt,
            'cost': cost,
            'is_enabled': is_enabled,
            'background_color': background_color,
            'is_user_input_required': is_user_input_required,
            'is_max_per_stream_enabled': is_max_per_stream_enabled,
            'max_per_stream': max_per_stream,
            'is_max_per_user_per_stream_enabled': is_max_per_user_per_stream_enabled,
            'max_per_user_per_stream': max_per_user_per_stream,
            'is_global_cooldown_enabled': is_global_cooldown_enabled,
            'global_cooldown_seconds': global_cooldown_seconds,
            'should_redemptions_skip_request_queue': should_redemptions_skip_request_queue
        }.items() if y is not None}
        result = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS], body)
        if result.status_code == 404:
            raise ValueError('Custom reward does not exist with the given reward_id for the given broadcaster')
        elif result.status_code == 403:
            raise TwitchAPIException('This custom reward was created by a different broadcaster or channel points are'
                                     'not available for the broadcaster')
        data = result.json()
        return make_fields_datetime(data, ['cooldown_expires_at'])

    def update_redemption_status(self,
                                 broadcaster_id: str,
                                 reward_id: str,
                                 redemption_ids: Union[List[str], str],
                                 status: CustomRewardRedemptionStatus) -> dict:
        """Updates the status of Custom Reward Redemption objects on a channel that
                are in the :code:`UNFULFILLED` status.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-redemption-status

        :param str broadcaster_id: Provided broadcaster_id must match the user_id in the auth token.
        :param str reward_id: ID of the Custom Reward the redemptions to be updated are for.
        :param union(list(str),str) redemption_ids: IDs of the Custom Reward Redemption to update, must match a
                    Custom Reward Redemption on broadcaster_id’s channel Max: 50 Can either be a list of str or str
        :param ~twitchAPI.types.CustomRewardRedemptionStatus status: The new status to set redemptions to.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.types.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        :raises ValueError: if redemption_ids is longer than 50 entries
        :raises ValueError: if no custom reward redemptions with status UNFULFILLED where found for the given ids
        :raises ~twitchAPI.types.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        :rtype: dict
        """
        if isinstance(redemption_ids, list) and len(redemption_ids) > 50:
            raise ValueError('redemption_ids cant have more than 50 entries')

        url = build_url(TWITCH_API_BASE_URL + 'channel_points/custom_rewards/redemptions',
                        {
                            'id': redemption_ids,
                            'broadcaster_id': broadcaster_id,
                            'reward_id': reward_id
                        }, split_lists=True)
        body = {'status': status.value}
        result = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS], data=body)
        if result.status_code == 404:
            raise ValueError('no custom reward redemptions with the specified ids where found '
                             'with a status of UNFULFILLED')
        if result.status_code == 403:
            raise TwitchAPIException('This custom reward was created by a different broadcaster or channel points are'
                                     'not available for the broadcaster')
        data = make_fields_datetime(result.json(), ['redeemed_at'])
        return fields_to_enum(data, ['status'], CustomRewardRedemptionStatus, CustomRewardRedemptionStatus.CANCELED)

    def get_channel_editors(self,
                            broadcaster_id: str) -> dict:
        """Gets a list of users who have editor permissions for a specific channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_EDITORS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-editors

        :param str broadcaster_id: Broadcaster’s user ID associated with the channel
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """

        url = build_url(TWITCH_API_BASE_URL + 'channels/editors', {'broadcaster_id': broadcaster_id})
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_EDITORS])
        return make_fields_datetime(result.json(), ['created_at'])

    def delete_videos(self,
                      video_ids: List[str]) -> Union[bool, dict]:
        """Deletes one or more videos. Videos are past broadcasts, Highlights, or uploads.
        Returns False if the User was not Authorized to delete at least one of the given videos.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_VIDEOS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-videos

        :param list(str) video_ids: ids of the videos, Limit: 5 ids
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if video_ids contains more than 5 entries or is a empty list
        :rtype: dict or False
        """
        if video_ids is None or len(video_ids) == 0 or len(video_ids) > 5:
            raise ValueError('video_ids must contain between 1 and 5 entries')
        url = build_url(TWITCH_API_BASE_URL + 'videos', {'id': video_ids}, split_lists=True)
        result = self.__api_delete_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_VIDEOS])
        if result.status_code == 200:
            return result.json()
        else:
            return False

    def get_user_block_list(self,
                            broadcaster_id: str,
                            first: Optional[int] = 20,
                            after: Optional[str] = None) -> dict:
        """Gets a specified user’s block list. The list is sorted by when the block occurred in descending order
        (i.e. most recent block first).

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.USER_READ_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-block-list

        :param str broadcaster_id: User ID for a twitch user
        :param int first: Maximum number of objects to return. Maximum: 100. |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """

        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        url = build_url(TWITCH_API_BASE_URL + 'users/blocks',
                        {'broadcaster_id': broadcaster_id,
                         'first': first,
                         'after': after}, remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.USER_READ_BLOCKED_USERS])
        return result.json()

    def block_user(self,
                   target_user_id: str,
                   source_context: Optional[BlockSourceContext] = None,
                   reason: Optional[BlockReason] = None) -> bool:
        """Blocks the specified user on behalf of the authenticated user.

         Requires User Authentication with :const:`twitchAPI.types.AuthScope.USER_MANAGE_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#block-user

        :param str target_user_id: User ID of the user to be blocked.
        :param ~twitchAPI.types.BlockSourceContext source_context: Source context for blocking the user. Optional
                    |default| :code:`None`
        :param ~twitchAPI.types.BlockReason reason: Reason for blocking the user. Optional. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: bool
        """
        url = build_url(TWITCH_API_BASE_URL + 'users/blocks',
                        {'target_user_id': target_user_id,
                         'source_context': enum_value_or_none(source_context),
                         'reason': enum_value_or_none(reason)},
                        remove_none=True)
        result = self.__api_put_request(url, AuthType.USER, [AuthScope.USER_MANAGE_BLOCKED_USERS])
        return result.status_code == 204

    def unblock_user(self,
                     target_user_id: str) -> bool:
        """Unblocks the specified user on behalf of the authenticated user.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.USER_MANAGE_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#unblock-user

        :param str target_user_id: User ID of the user to be unblocked.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: bool
        """
        url = build_url(TWITCH_API_BASE_URL + 'users/blocks', {'target_user_id': target_user_id})
        result = self.__api_delete_request(url, AuthType.USER, [AuthScope.USER_MANAGE_BLOCKED_USERS])
        return result.status_code == 204

    def get_followed_streams(self,
                             user_id: str,
                             after: Optional[str] = None,
                             first: Optional[int] = 100) -> dict:
        """Gets information about active streams belonging to channels that the authenticated user follows.
        Streams are returned sorted by number of current viewers, in descending order.
        Across multiple pages of results, there may be duplicate or missing streams, as viewers join and leave streams.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.USER_READ_FOLLOWS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-followed-streams

        :param str user_id: Results will only include active streams from the channels that this Twitch user follows.
                user_id must match the User ID in the bearer token.
        :param str after: Cursor for forward pagination. |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum 100 |default| :code:`100`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        :rtype: dict
        """
        if first < 1 or first > 100:
            raise ValueError('first must be in range 1 to 100')
        url = build_url(TWITCH_API_BASE_URL + 'streams/followed',
                        {
                            'user_id': user_id,
                            'after': after,
                            'first': first},
                        remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.USER_READ_FOLLOWS])
        return make_fields_datetime(result.json(), ['started_at'])

    def get_polls(self,
                  broadcaster_id: str,
                  poll_id: Optional[str] = None,
                  after: Optional[str] = None,
                  first: Optional[int] = 20) -> dict:
        """Get information about all polls or specific polls for a Twitch channel.
        Poll information is available for 90 days.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-polls

        :param str broadcaster_id: The broadcaster running polls.
                Provided broadcaster_id must match the user_id in the user OAuth token.
        :param str poll_id: ID of a poll. |default| :code:`None`
        :param str after: Cursor for forward pagination. |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum 20 |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 20
        :rtype: dict
        """
        if first is not None and (first < 1 or first > 20):
            raise ValueError('first must be in range 1 to 20')
        url = build_url(TWITCH_API_BASE_URL + 'polls',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': poll_id,
                            'after': after,
                            'first': first
                        },
                        remove_none=True)
        result = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_POLLS]).json()
        return make_fields_datetime(result, ['started_at', 'ended_at'])

    def create_poll(self,
                    broadcaster_id: str,
                    title: str,
                    choices: List[str],
                    duration: int,
                    bits_voting_enabled: bool = False,
                    bits_per_vote: Optional[int] = None,
                    channel_points_voting_enabled: bool = False,
                    channel_points_per_vote: Optional[int] = None) -> dict:
        """Create a poll for a specific Twitch channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-polls

        :param str broadcaster_id: The broadcaster running the poll
        :param str title: Question displayed for the poll
        :param List[str] choices: List of poll choices.
        :param int duration: Total duration for the poll (in seconds). Minimum 15, Maximum 1800
        :param bool bits_voting_enabled: Indicates if Bits can be used for voting. |default| :code:`False`
        :param int bits_per_vote: Number of Bits required to vote once with Bits.
            Minimum: 0. Maximum: 10000. |default| :code:`None`
        :param bool channel_points_voting_enabled: Indicates if Channel Points can be used for voting. |default| :code:`False`
        :param int channel_points_per_vote: Number of Channel Points required to vote once with Channel Points.
            Minimum: 0. Maximum: 1000000. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if duration is not in range 15 to 1800
        :raises ValueError: if bits_per_vote is not in range 0 to 10000
        :raises ValueError: if channel_points_per_vote is not in range 0 to 1000000
        :rtype: dict
        """
        if duration < 15 or duration > 1800:
            raise ValueError('duration must be between 15 and 1800')
        if bits_per_vote is not None:
            if bits_per_vote < 0 or bits_per_vote > 10000:
                raise ValueError('bits_per_vote must be in range 0 to 10000')
        if channel_points_per_vote is not None:
            if channel_points_per_vote < 0 or channel_points_per_vote > 1_000_000:
                raise ValueError('channel_points_per_vote must be in range 0 to 1000000')
        if len(choices) < 0 or len(choices) > 5:
            raise ValueError('require between 2 and 5 choices')
        body = {k: v for k, v in {
                    'broadcaster_id': broadcaster_id,
                    'title': title,
                    'choices': [{'title': x} for x in choices],
                    'duration': duration,
                    'bits_voting_enabled': bits_voting_enabled,
                    'bits_per_vote': bits_per_vote,
                    'channel_points_voting_enabled': channel_points_voting_enabled,
                    'channel_points_per_vote': channel_points_per_vote
                }.items() if v is not None}

        url = build_url(TWITCH_API_BASE_URL + 'polls', {})
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_POLLS], data=body).json()
        return make_fields_datetime(result, ['started_at', 'ended_at'])

    def end_poll(self,
                 broadcaster_id: str,
                 poll_id: str,
                 status: PollStatus) -> dict:
        """End a poll that is currently active.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#end-poll

        :param str broadcaster_id: id of the broadcaster running the poll
        :param str poll_id: id of the poll
        :param ~twitchAPI.types.PollStatus status: The poll status to be set
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if status is not TERMINATED or ARCHIVED
        :rtype: dict
        """
        if status not in (PollStatus.TERMINATED, PollStatus.ARCHIVED):
            raise ValueError('status must be either TERMINATED or ARCHIVED')
        url = build_url(TWITCH_API_BASE_URL + 'polls', {})
        body = {
            'broadcaster_id': broadcaster_id,
            'id': poll_id,
            status: status.value
        }
        result = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_POLLS], data=body).json()
        result = fields_to_enum(result, ['status'], PollStatus, PollStatus.ACTIVE)
        return make_fields_datetime(result, ['started_at', 'ended_at'])

    def get_predictions(self,
                        broadcaster_id: str,
                        prediction_ids: Optional[List[str]] = None,
                        after: Optional[str] = None,
                        first: Optional[int] = 20) -> dict:
        """Get information about all Channel Points Predictions or specific Channel Points Predictions for a Twitch channel.
        Results are ordered by most recent, so it can be assumed that the currently active or locked Prediction will be the first item.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-predictions

        :param str broadcaster_id: The broadcaster running the prediction
        :param List[str] prediction_ids: List of prediction ids. |default| :code:`None`
        :param str after: Cursor for forward pagination. |default| :code:`None`
        :param int first: Maximum number of objects to return. Maximum 20 |default| :code:`20`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 20
        :raises ValueError: if prediction_ids contains more than 100 entries
        :rtype: dict
        """
        if first is not None and (first < 1 or first > 20):
            raise ValueError('first must be in range 1 to 20')
        if prediction_ids is not None:
            if len(prediction_ids) > 100:
                raise ValueError('maximum of 100 prediction ids allowed')

        url = build_url(TWITCH_API_BASE_URL + 'predictions',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': prediction_ids,
                            'after': after,
                            'first': first
                        }, remove_none=True, split_lists=True)
        data = self.__api_get_request(url, AuthType.USER, [AuthScope.CHANNEL_READ_PREDICTIONS])
        return make_fields_datetime(data.json(), ['created_at', 'ended_at', 'locked_at'])

    def create_prediction(self,
                          broadcaster_id: str,
                          title: str,
                          outcomes: List[str],
                          prediction_window: int) -> dict:
        """Create a Channel Points Prediction for a specific Twitch channel.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-predictions

        :param str broadcaster_id: The broadcaster running the prediction
        :param str title: Title of the Prediction
        :param list[str] outcomes: List of possible Outcomes, must contain exactly 2 entries
        :param int prediction_window: Total duration for the Prediction (in seconds). Minimum 1, Maximum 1800
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if prediction_window is not in range 1 to 1800
        :raises ValueError: if outcomes does not contain exactly 2 entries
        :rtype: dict
        """
        if prediction_window < 1 or prediction_window > 1800:
            raise ValueError('prediction_window must be in range 1 to 1800')
        if len(outcomes) != 2:
            raise ValueError('outcomes requires exactly 2 entries')
        body = {
            'broadcaster_id': broadcaster_id,
            'title': title,
            'outcomes': [{'title': x} for x in outcomes],
            'prediction_window': prediction_window
        }
        url = build_url(TWITCH_API_BASE_URL + 'predictions', {})
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_PREDICTIONS], data=body)
        return make_fields_datetime(result.json(), ['created_at', 'ended_at', 'locked_at'])

    def end_prediction(self,
                       broadcaster_id: str,
                       prediction_id: str,
                       status: PredictionStatus,
                       winning_outcome_id: Optional[str] = None):
        """Lock, resolve, or cancel a Channel Points Prediction.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#end-prediction

        :param str broadcaster_id: ID of the broadcaster
        :param str prediction_id: ID of the Prediction
        :param ~twitchAPI.types.PredictionStatus status: The Prediction status to be set.
        :param str winning_outcome_id: ID of the winning outcome for the Prediction. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if winning_outcome_id is None and status is RESOLVED
        :raises ValueError: if status is not one of RESOLVED, CANCELED or LOCKED
        :rtype: dict
        """
        if status not in (PredictionStatus.RESOLVED, PredictionStatus.CANCELED, PredictionStatus.LOCKED):
            raise ValueError('status has to be one of RESOLVED, CANCELED or LOCKED')
        if status == PredictionStatus.RESOLVED:
            if winning_outcome_id is None:
                raise ValueError('need to specify winning_outcome_id for status RESOLVED')
        body = {
            'broadcaster_id': broadcaster_id,
            'id': prediction_id,
            'status': status.value
        }
        if winning_outcome_id is not None:
            body['winning_outcome_id'] = winning_outcome_id
        url = build_url(TWITCH_API_BASE_URL + 'predictions', {})
        result = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_PREDICTIONS], data=body)
        return make_fields_datetime(result.json(), ['created_at', 'ended_at', 'locked_at'])

    def manage_held_automod_message(self,
                                    user_id: str,
                                    msg_id: str,
                                    action: AutoModAction) -> bool:
        """Allow or deny a message that was held for review by AutoMod.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.MODERATOR_MANAGE_AUTOMOD`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#manage-held-automod-messages

        :param str user_id: The moderator who is approving or rejecting the held message.
        :param str msg_id: ID of the targeted message
        :param ~twitchAPI.types.AutoModAction action: The action to take for the message.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        body = {
            'user_id': user_id,
            'msg_id': msg_id,
            'action': action.value
        }
        url = build_url(TWITCH_API_BASE_URL + 'moderation/automod/message', {})
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.MODERATOR_MANAGE_AUTOMOD], data=body)
        return result.status_code == 200

    def get_chat_badges(self, broadcaster_id: str) -> dict:
        """Gets a list of custom chat badges that can be used in chat for the specified channel.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-chat-badges

        :param broadcaster_id:
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'chat/badges', {'broadcaster_id': broadcaster_id})
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def get_global_chat_badges(self) -> dict:
        """Gets a list of chat badges that can be used in chat for any channel.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-global-chat-badges

        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'chat/badges/global', {})
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def get_channel_emotes(self, broadcaster_id: str) -> dict:
        """Gets all emotes that the specified Twitch channel created.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-emotes

        :param str broadcaster_id: ID of the broadcaster
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'chat/emotes',
                        {'broadcaster_id': broadcaster_id})
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def get_global_emotes(self) -> dict:
        """Gets all global emotes.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-global-emotes

        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'chat/emotes/global', {})
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def get_emote_sets(self, emote_set_id: List[str]) -> dict:
        """Gets emotes for one or more specified emote sets.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-emote-sets

        :param list[str] emote_set_id: A list of IDs that identify the emote sets.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'chat/emotes/set', {'emote_set_id': emote_set_id}, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, [])
        return result.json()

    def delete_eventsub_subscription(self, subscription_id: str) -> bool:
        """Deletes an EventSub subscription.

        Requires App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-eventsub-subscription

        :param str subscription_id: The ID of the subscription
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: bool
        """
        url = build_url(TWITCH_API_BASE_URL + 'eventsub/subscriptions', {'id': subscription_id})
        result = self.__api_delete_request(url, AuthType.APP, [])
        return result.status_code == 204

    def get_eventsub_subscriptions(self,
                                   status: Optional[str] = None,
                                   sub_type: Optional[str] = None,
                                   after: Optional[str] = None):
        """Gets a list of your EventSub subscriptions.
        The list is paginated and ordered by the oldest subscription first.

        Requires App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-eventsub-subscriptions

        :param str status: Filter subscriptions by its status. |default| :code:`None`
        :param str sub_type: Filter subscriptions by subscription type. |default| :code:`None`
        :param str after: The cursor used to get the next page of results. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'eventsub/subscriptions',
                        {
                            'status': status,
                            'type': sub_type,
                            'after': after
                        }, remove_none=True)
        result = self.__api_get_request(url, AuthType.APP, [])
        return result.json()

    def get_channel_stream_schedule(self,
                                    broadcaster_id: str,
                                    stream_segment_ids: Optional[List[str]] = None,
                                    start_time: Optional[datetime] = None,
                                    utc_offset: Optional[str] = None,
                                    first: Optional[int] = 20,
                                    after: Optional[str] = None) -> dict:
        """Gets all scheduled broadcasts or specific scheduled broadcasts from a channel’s stream schedule.

        Requires App or User Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-stream-schedule

        :param str broadcaster_id: user id of the broadcaster
        :param list[str] stream_segment_ids: optional list of stream segment ids. Maximum 100 entries. |default| :code:`None`
        :param ~datetime.datetime start_time: optional timestamp to start returning stream segments from. |default| :code:`None`
        :param str utc_offset: A timezone offset to be used. |default| :code:`None`
        :param int first: Maximum Number of stream segments to return. Maximum 25. |default| :code:`20`
        :param str after: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if stream_segment_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 25
        :rtype: dict
        """
        if stream_segment_ids is not None and len(stream_segment_ids) > 100:
            raise ValueError('stream_segment_ids can only have 100 entries')
        if first is not None and (first > 25 or first < 1):
            raise ValueError('first has to be in range 1 to 25')
        url = build_url(TWITCH_API_BASE_URL + 'schedule',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': stream_segment_ids,
                            'start_time': datetime_to_str(start_time),
                            'utc_offset': utc_offset,
                            'first': first,
                            'after': after
                        }, remove_none=True, split_lists=True)
        result = self.__api_get_request(url, AuthType.EITHER, []).json()
        return make_fields_datetime(result, ['start_time', 'end_time'])

    def get_channel_icalendar(self, broadcaster_id: str) -> str:
        """Gets all scheduled broadcasts from a channel’s stream schedule as an iCalendar.

        Does not require Authorization\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-icalendar

        :param str broadcaster_id: id of the broadcaster
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: str
        """
        url = build_url(TWITCH_API_BASE_URL + 'schedule/icalendar', {'broadcaster_id': broadcaster_id})
        return self.__api_get_request(url, AuthType.NONE, []).text

    def update_channel_stream_schedule(self,
                                       broadcaster_id: str,
                                       is_vacation_enabled: Optional[bool] = None,
                                       vacation_start_time: Optional[datetime] = None,
                                       vacation_end_time: Optional[datetime] = None,
                                       timezone: Optional[str] = None) -> bool:
        """Update the settings for a channel’s stream schedule. This can be used for setting vacation details.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-channel-stream-schedule

        :param str broadcaster_id: id of the broadcaster
        :param bool is_vacation_enabled: indicates if Vacation Mode is enabled. |default| :code:`None`
        :param ~datetime.datetime vacation_start_time: Start time for vacation |default| :code:`None`
        :param ~datetime.datetime vacation_end_time: End time for vacation specified |default| :code:`None`
        :param str timezone: The timezone for when the vacation is being scheduled using the IANA time zone database format.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: bool
        """
        url = build_url(TWITCH_API_BASE_URL + 'schedule/settings',
                        {
                            'broadcaster_id': broadcaster_id,
                            'is_vacation_enabled': is_vacation_enabled,
                            'vacation_start_time': datetime_to_str(vacation_start_time),
                            'vacation_end_time': datetime_to_str(vacation_end_time),
                            'timezone': timezone
                        }, remove_none=True)
        return self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE]).status_code == 200

    def create_channel_stream_schedule_segment(self,
                                               broadcaster_id: str,
                                               start_time: datetime,
                                               timezone: str,
                                               is_recurring: bool,
                                               duration: Optional[str] = None,
                                               category_id: Optional[str] = None,
                                               title: Optional[str] = None) -> dict:
        """Create a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-channel-stream-schedule-segment

        :param str broadcaster_id: id of the broadcaster
        :param datetime start_time: Start time for the scheduled broadcast
        :param str timezone: The timezone of the application creating the scheduled broadcast using the IANA time zone database format.
        :param bool is_recurring: Indicates if the scheduled broadcast is recurring weekly.
        :param str duration: Duration of the scheduled broadcast in minutes from the start_time. |default| :code:`240`
        :param str category_id: Game/Category ID for the scheduled broadcast. |default| :code:`None`
        :param str title: Title for the scheduled broadcast. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'schedule/segment', {'broadcaster_id': broadcaster_id})
        body = remove_none_values({
            'start_time': datetime_to_str(start_time),
            'timezone': timezone,
            'is_recurring': is_recurring,
            'duration': duration,
            'category_id': category_id,
            'title': title
        })
        result = self.__api_post_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE], data=body).json()
        return make_fields_datetime(result, ['start_time', 'end_time'])

    def update_channel_stream_schedule_segment(self,
                                               broadcaster_id: str,
                                               stream_segment_id: str,
                                               start_time: Optional[datetime] = None,
                                               duration: Optional[str] = None,
                                               category_id: Optional[str] = None,
                                               title: Optional[str] = None,
                                               is_canceled: Optional[bool] = None,
                                               timezone: Optional[str] = None) -> dict:
        """Update a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-channel-stream-schedule-segment

        :param str broadcaster_id: id of the broadcaster
        :param str stream_segment_id: The ID of the streaming segment to update.
        :param ~datetime.datetime start_time: Start time for the scheduled broadcast |default| :code:`None`
        :param str duration: Duration of the scheduled broadcast in minutes from the start_time. |default| :code:`240`
        :param str category_id: Game/Category ID for the scheduled broadcast. |default| :code:`None`
        :param str title: Title for the scheduled broadcast. |default| :code:`None`
        :param bool is_canceled: Indicated if the scheduled broadcast is canceled. |default| :code:`None`
        :param str timezone: The timezone of the application creating the scheduled broadcast using the IANA time zone database format. |default| :code:`None`
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: dict
        """
        url = build_url(TWITCH_API_BASE_URL + 'schedule/segment',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': stream_segment_id
                        })
        body = remove_none_values({
            'start_time': datetime_to_str(start_time),
            'duration': duration,
            'category_id': category_id,
            'title': title,
            'is_canceled': is_canceled,
            'timezone': timezone
        })
        result = self.__api_patch_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE], data=body)
        return make_fields_datetime(result.json(), ['start_time', 'end_time'])

    def delete_channel_stream_schedule_segment(self,
                                               broadcaster_id: str,
                                               stream_segment_id: str) -> bool:
        """Delete a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`twitchAPI.types.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-channel-stream-schedule-segment

        :param str broadcaster_id: id of the broadcaster
        :param str stream_segment_id: The ID of the streaming segment to delete.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :rtype: bool
        """
        url = build_url(TWITCH_API_BASE_URL + 'schedule/segment',
                        {
                            'broadcaster_id': broadcaster_id,
                            'id': stream_segment_id
                        })
        return self.__api_delete_request(url, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE]).status_code == 204

    def update_drops_entitlements(self,
                                  entitlement_ids: List[str],
                                  fulfillment_status: EntitlementFulfillmentStatus) -> dict:
        """Updates the fulfillment status on a set of Drops entitlements, specified by their entitlement IDs.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-drops-entitlements

        :param list[str] entitlement_ids: An array of unique identifiers of the entitlements to update.
        :param ~twitchAPI.types.EntitlementFulfillmentStatus fulfillment_status: A fulfillment status.
        :raises ~twitchAPI.types.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.types.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.types.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.types.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.types.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if entitlement_ids has more than 100 entries
        :rtype: dict
        """
        if len(entitlement_ids) > 100:
            raise ValueError('entitlement_ids can only have a maximum of 100 entries')
        url = build_url(TWITCH_API_BASE_URL + 'entitlements/drops', {})
        body = remove_none_values({
            'entitlement_ids': entitlement_ids,
            'fulfillment_status': fulfillment_status.value
        })
        return self.__api_patch_request(url, AuthType.EITHER, [], data=body).json()

