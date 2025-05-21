#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Twitch API
----------

This is the base of this library, it handles authentication renewal, error handling and permission management.

Look at the `Twitch API reference <https://dev.twitch.tv/docs/api/reference>`__ for a more detailed documentation on
what each endpoint does.

*************
Example Usage
*************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    import asyncio

    async def twitch_example():
        # initialize the twitch instance, this will by default also create a app authentication for you
        twitch = await Twitch('app_id', 'app_secret')
        # call the API for the data of your twitch user
        # this returns a async generator that can be used to iterate over all results
        # but we are just interested in the first result
        # using the first helper makes this easy.
        user = await first(twitch.get_users(logins='your_twitch_user'))
        # print the ID of your user or do whatever else you want with it
        print(user.id)
        await twitch.close()

    # run this example
    asyncio.run(twitch_example())


****************************
Working with the API results
****************************

The API returns a few different types of results.


TwitchObject
============

A lot of API calls return a child of :py:const:`~twitchAPI.object.TwitchObject` in some way (either directly or via generator).
You can always use the :py:const:`~twitchAPI.object.TwitchObject.to_dict()` method to turn that object to a dictionary.

Example:

.. code-block:: python

    blocked_term = await twitch.add_blocked_term('broadcaster_id', 'moderator_id', 'bad_word')
    print(blocked_term.id)


IterTwitchObject
================

Some API calls return a special type of TwitchObject.
These usually have some list inside that you may want to directly iterate over in your API usage but that also contain other useful data
outside of that List.


Example:

.. code-block:: python

    lb = await twitch.get_bits_leaderboard()
    print(lb.total)
    for e in lb:
        print(f'#{e.rank:02d} - {e.user_name}: {e.score}')


AsyncIterTwitchObject
=====================

A few API calls will have useful data outside of the list the pagination iterates over.
For those cases, this object exist.

Example:

.. code-block:: python

    schedule = await twitch.get_channel_stream_schedule('user_id')
    print(schedule.broadcaster_name)
    async for segment in schedule:
        print(segment.title)


AsyncGenerator
==============

AsyncGenerators are used to automatically iterate over all possible results of your API call, this will also automatically handle pagination for you.
In some cases (for example stream schedules with repeating entries), this may result in a endless stream of entries returned so make sure to add your
own exit conditions in such cases.
The generated objects will always be children of :py:const:`~twitchAPI.object.TwitchObject`, see the docs of the API call to see the exact
object type.

Example:

.. code-block:: python

    async for tag in twitch.get_all_stream_tags():
        print(tag.tag_id)

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
    twitch = await Twitch('my_app_id', 'my_app_secret')

You can set a Auth Scope like this:

.. code-block:: python

    from twitchAPI.twitch import Twitch, AuthScope
    twitch = await Twitch('my_app_id', 'my_app_secret', target_app_auth_scope=[AuthScope.USER_EDIT])

If you want to change the AuthScope later use this:

.. code-block:: python

    await twitch.authenticate_app(my_new_scope)


If you don't want to use App Authentication, Initialize like this:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = await Twitch('my_app_id', authenticate_app=False)


User Authentication
===================

Only use a user auth token, use this:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = await Twitch('my_app_id', authenticate_app=False)
    # make sure to set the second parameter as the scope used to generate the token
    await twitch.set_user_authentication('token', [], 'refresh_token')


Use both App and user Authentication:

.. code-block:: python

    from twitchAPI.twitch import Twitch
    twitch = await Twitch('my_app_id', 'my_app_secret')
    # make sure to set the second parameter as the scope used to generate the token
    await twitch.set_user_authentication('token', [], 'refresh_token')


To get a user auth token, the user has to explicitly click "Authorize" on the twitch website. You can use various online
services to generate a token or use my build in authenticator.

See :obj:`twitchAPI.oauth` for more info on my build in authenticator.

Authentication refresh callback
===============================

Optionally you can set a callback for both user access token refresh and app access token refresh.

.. code-block:: python

    from twitchAPI.twitch import Twitch

    async def user_refresh(token: str, refresh_token: str):
        print(f'my new user token is: {token}')

    async def app_refresh(token: str):
        print(f'my new app token is: {token}')

    twitch = await Twitch('my_app_id', 'my_app_secret')
    twitch.app_auth_refresh_callback = app_refresh
    twitch.user_auth_refresh_callback = user_refresh

*******************
Class Documentation
*******************
"""
import asyncio
import aiohttp.helpers
from datetime import datetime
from aiohttp import ClientSession, ClientResponse
from aiohttp.client import ClientTimeout
from twitchAPI.helper import (
    TWITCH_API_BASE_URL, TWITCH_AUTH_BASE_URL, build_scope, enum_value_or_none, datetime_to_str, remove_none_values, ResultType, build_url)
from logging import getLogger, Logger
from twitchAPI.object.base import TwitchObject
from twitchAPI.object.api import (
    TwitchUser, ExtensionAnalytic, GameAnalytics, CreatorGoal, BitsLeaderboard, ExtensionTransaction, ChatSettings, CreatedClip, Clip, 
    Game, AutoModStatus, BannedUser, BanUserResponse, BlockedTerm, Moderator, CreateStreamMarkerResponse, Stream, GetStreamMarkerResponse,
    BroadcasterSubscriptions, UserSubscription, ChannelTeam, UserExtension, UserActiveExtensions, Video, ChannelInformation, SearchChannelResult,
    SearchCategoryResult, StartCommercialResult, GetCheermotesResponse, HypeTrainEvent, DropsEntitlement, CustomReward,
    CustomRewardRedemption, ChannelEditor, BlockListEntry, Poll, Prediction, RaidStartResult, ChatBadge, GetChannelEmotesResponse,
    GetEmotesResponse, GetEventSubSubscriptionResult, ChannelStreamSchedule, ChannelVIP, UserChatColor, GetChattersResponse, ShieldModeStatus,
    CharityCampaign, CharityCampaignDonation, AutoModSettings, ChannelFollowersResult, FollowedChannelsResult, ContentClassificationLabel, 
    AdSchedule, AdSnoozeResponse, SendMessageResponse, ChannelModerator, UserEmotesResponse, WarnResponse, SharedChatSession)
from twitchAPI.type import (
    AnalyticsReportType, AuthScope, TimePeriod, SortMethod, VideoType, AuthType, CustomRewardRedemptionStatus, SortOrder,
    BlockSourceContext, BlockReason, EntitlementFulfillmentStatus, PollStatus, PredictionStatus, AutoModAction,
    AutoModCheckEntry, TwitchAPIException, InvalidTokenException, TwitchAuthorizationException,
    UnauthorizedException, MissingScopeException, TwitchBackendException, MissingAppSecretException, TwitchResourceNotFound, ForbiddenError)
from typing import Sequence, Union, List, Optional, Callable, AsyncGenerator, TypeVar, Awaitable, Type, Mapping, overload, Tuple

__all__ = ['Twitch']
T = TypeVar('T', bound=TwitchObject)


class Twitch:
    """
    Twitch API client
    """

    def __init__(self,
                 app_id: str,
                 app_secret: Optional[str] = None,
                 authenticate_app: bool = True,
                 target_app_auth_scope: Optional[List[AuthScope]] = None,
                 base_url: str = TWITCH_API_BASE_URL,
                 auth_base_url: str = TWITCH_AUTH_BASE_URL,
                 session_timeout: Union[object, ClientTimeout] = aiohttp.helpers.sentinel):
        """
        :param app_id: Your app id
        :param app_secret: Your app secret, leave as None if you only want to use User Authentication |default| :code:`None`
        :param authenticate_app: If true, auto generate a app token on startup |default| :code:`True`
        :param target_app_auth_scope: AuthScope to use if :code:`authenticate_app` is True |default| :code:`None`
        :param base_url: The URL to the Twitch API |default| :const:`~twitchAPI.helper.TWITCH_API_BASE_URL`
        :param auth_base_url: The URL to the Twitch API auth server |default| :const:`~twitchAPI.helper.TWITCH_AUTH_BASE_URL`
        :param session_timeout: Override the time in seconds before any request times out. Defaults to aiohttp default (300 seconds)
        """
        self.app_id: str = app_id
        self.app_secret: Optional[str] = app_secret
        self.logger: Logger = getLogger('twitchAPI.twitch')
        """The logger used for Twitch API call related log messages"""
        self.user_auth_refresh_callback: Optional[Callable[[str, str], Awaitable[None]]] = None
        """If set, gets called whenever a user auth token gets refreshed. Parameter: Auth Token, Refresh Token |default| :code:`None`"""
        self.app_auth_refresh_callback: Optional[Callable[[str], Awaitable[None]]] = None
        """If set, gets called whenever a app auth token gets refreshed. Parameter: Auth Token |default| :code:`None`"""
        self.session_timeout: Union[object, ClientTimeout] = session_timeout
        """Override the time in seconds before any request times out. Defaults to aiohttp default (300 seconds)"""
        self._app_auth_token: Optional[str] = None
        self._app_auth_scope: List[AuthScope] = []
        self._has_app_auth: bool = False
        self._user_auth_token: Optional[str] = None
        self._user_auth_refresh_token: Optional[str] = None
        self._user_auth_scope: List[AuthScope] = []
        self._has_user_auth: bool = False
        self.auto_refresh_auth: bool = True
        """If set to true, auto refresh the auth token once it expires. |default| :code:`True`"""
        self._authenticate_app = authenticate_app
        self._target_app_scope = target_app_auth_scope
        self.base_url: str = base_url
        """The URL to the Twitch API used"""
        self.auth_base_url: str = auth_base_url
        self._user_token_refresh_lock: bool = False
        self._app_token_refresh_lock: bool = False

    def __await__(self):
        if self._authenticate_app:
            t = asyncio.create_task(self.authenticate_app(self._target_app_scope if self._target_app_scope is not None else []))
            yield from t
        return self

    @staticmethod
    async def close():
        """Gracefully close the connection to the Twitch API"""
        # ensure that asyncio actually gracefully shut down
        await asyncio.sleep(0.25)

    def _generate_header(self, auth_type: 'AuthType', required_scope: List[Union[AuthScope, List[AuthScope]]]) -> dict:
        header = {"Client-ID": self.app_id}
        if auth_type == AuthType.EITHER:
            has_auth, target, token, scope = self._get_used_either_auth(required_scope) # type: ignore
            if not has_auth:
                raise UnauthorizedException('No authorization with correct scope set!')
            header['Authorization'] = f'Bearer {token}'
        elif auth_type == AuthType.APP:
            if not self._has_app_auth:
                raise UnauthorizedException('Require app authentication!')
            for s in required_scope:
                if isinstance(s, list):
                    if not any([x in self._app_auth_scope for x in s]):
                        raise MissingScopeException(f'Require at least one of the following app auth scopes: {", ".join([x.name for x in s])}')
                else:
                    if s not in self._app_auth_scope:
                        raise MissingScopeException('Require app auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self._app_auth_token}'
        elif auth_type == AuthType.USER:
            if not self._has_user_auth:
                raise UnauthorizedException('require user authentication!')
            for s in required_scope:
                if isinstance(s, list):
                    if not any([x in self._user_auth_scope for x in s]):
                        raise MissingScopeException(f'Require at least one of the following user auth scopes: {", ".join([x.name for x in s])}')
                else:
                    if s not in self._user_auth_scope:
                        raise MissingScopeException('Require user auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self._user_auth_token}'
        elif auth_type == AuthType.NONE:
            # set one anyway for better performance if possible but don't error if none found
            has_auth, target, token, scope = self._get_used_either_auth(required_scope) # type: ignore
            if has_auth:
                header['Authorization'] = f'Bearer {token}'
        return header

    def _get_used_either_auth(self, required_scope: List[AuthScope]) -> Tuple[bool, AuthType, Union[None, str], List[AuthScope]]:
        if self.has_required_auth(AuthType.USER, required_scope):
            return True, AuthType.USER, self._user_auth_token, self._user_auth_scope
        if self.has_required_auth(AuthType.APP, required_scope):
            return True, AuthType.APP, self._app_auth_token, self._app_auth_scope
        return False, AuthType.NONE, None, []

    def get_user_auth_scope(self) -> List[AuthScope]:
        """Returns the set User auth Scope"""
        return self._user_auth_scope

    def has_required_auth(self, required_type: AuthType, required_scope: List[AuthScope]) -> bool:
        if required_type == AuthType.NONE:
            return True
        if required_type == AuthType.EITHER:
            return self.has_required_auth(AuthType.USER, required_scope) or \
                   self.has_required_auth(AuthType.APP, required_scope)
        if required_type == AuthType.USER:
            if not self._has_user_auth:
                return False
            for s in required_scope:
                if s not in self._user_auth_scope:
                    return False
            return True
        if required_type == AuthType.APP:
            if not self._has_app_auth:
                return False
            for s in required_scope:
                if s not in self._app_auth_scope:
                    return False
            return True
        # default to false
        return False

    # FIXME rewrite refresh_used_token
    async def refresh_used_token(self):
        """Refreshes the currently used token"""
        if self._has_user_auth:
            from .oauth import refresh_access_token
            if self._user_token_refresh_lock:
                while self._user_token_refresh_lock:
                    await asyncio.sleep(0.1)
            else:
                self.logger.debug('refreshing user token')
                self._user_token_refresh_lock = True
                self._user_auth_token, self._user_auth_refresh_token = await refresh_access_token(self._user_auth_refresh_token, # type: ignore
                                                                                                  self.app_id,
                                                                                                  self.app_secret, # type: ignore
                                                                                                  auth_base_url=self.auth_base_url)
                self._user_token_refresh_lock = False
                if self.user_auth_refresh_callback is not None:
                    await self.user_auth_refresh_callback(self._user_auth_token, self._user_auth_refresh_token) # type: ignore
        else:
            await self._refresh_app_token()

    async def _refresh_app_token(self):
        if self._app_token_refresh_lock:
            while self._app_token_refresh_lock:
                await asyncio.sleep(0.1)
        else:
            self._app_token_refresh_lock = True
            self.logger.debug('refreshing app token')
            await self._generate_app_token()
            self._app_token_refresh_lock = False
            if self.app_auth_refresh_callback is not None:
                await self.app_auth_refresh_callback(self._app_auth_token) # type: ignore

    async def _check_request_return(self,
                                    session: ClientSession,
                                    response: ClientResponse,
                                    method: str,
                                    url: str,
                                    auth_type: 'AuthType',
                                    required_scope: List[Union[AuthScope, List[AuthScope]]],
                                    data: Optional[dict] = None,
                                    retries: int = 1
                                    ) -> ClientResponse:
        if retries > 0:
            if response.status == 503:
                # service unavailable, retry exactly once as recommended by twitch documentation
                self.logger.debug('got 503 response -> retry once')
                return await self._api_request(method, session, url, auth_type, required_scope, data=data, retries=retries - 1)
            elif response.status == 401:
                if self.auto_refresh_auth:
                    # unauthorized, lets try to refresh the token once
                    self.logger.debug('got 401 response -> try to refresh token')
                    await self.refresh_used_token()
                    return await self._api_request(method, session, url, auth_type, required_scope, data=data, retries=retries - 1)
                else:
                    msg = (await response.json()).get('message', '')
                    self.logger.debug(f'got 401 response and can\'t refresh. Message: "{msg}"')
                    raise UnauthorizedException(msg)
        else:
            if response.status == 503:
                raise TwitchBackendException('The Twitch API returns a server error')
            elif response.status == 401:
                msg = (await response.json()).get('message', '')
                self.logger.debug(f'got 401 response and can\'t refresh. Message: "{msg}"')
                raise UnauthorizedException(msg)

        if response.status == 500:
            raise TwitchBackendException('Internal Server Error')
        if response.status == 400:
            msg = None
            try:
                msg = (await response.json()).get('message')
            except BaseException:
                pass
            raise TwitchAPIException('Bad Request' + ('' if msg is None else f' - {str(msg)}'))
        if response.status == 404:
            msg = None
            try:
                msg = (await response.json()).get('message')
            except BaseException:
                pass
            raise TwitchResourceNotFound(msg)
        if response.status == 429 or str(response.headers.get('Ratelimit-Remaining', '')) == '0':
            self.logger.warning('reached rate limit, waiting for reset')
            import time
            reset = int(response.headers['Ratelimit-Reset'])
            # wait a tiny bit longer to ensure that we are definitely beyond the rate limit
            await asyncio.sleep((reset - time.time()) + 0.1)
        return response

    async def _api_request(self,
                           method: str,
                           session: ClientSession,
                           url: str,
                           auth_type: 'AuthType',
                           required_scope: List[Union[AuthScope, List[AuthScope]]],
                           data: Optional[dict] = None,
                           retries: int = 1) -> ClientResponse:
        """Make API request"""
        headers = self._generate_header(auth_type, required_scope)
        self.logger.debug(f'making {method} request to {url}')
        req = await session.request(method, url, headers=headers, json=data)
        return await self._check_request_return(session, req, method, url, auth_type, required_scope, data, retries)

    async def _build_generator(self,
                               method: str,
                               url: str,
                               url_params: dict,
                               auth_type: AuthType,
                               auth_scope: List[Union[AuthScope, List[AuthScope]]],
                               return_type: Type[T],
                               body_data: Optional[dict] = None,
                               split_lists: bool = False,
                               error_handler: Optional[Mapping[int, BaseException]] = None) -> AsyncGenerator[T, None]:
        _after = url_params.get('after')
        _first = True
        async with ClientSession(timeout=self.session_timeout) as session:
            while _first or _after is not None:
                url_params['after'] = _after
                _url = build_url(self.base_url + url, url_params, remove_none=True, split_lists=split_lists)
                response = await self._api_request(method, session, _url, auth_type, auth_scope, data=body_data)
                if error_handler is not None:
                    if response.status in error_handler.keys():
                        raise error_handler[response.status]
                data = await response.json()
                for entry in data.get('data', []):
                    yield return_type(**entry)
                _after = data.get('pagination', {}).get('cursor')
                _first = False

    async def _build_iter_result(self,
                                 method: str,
                                 url: str,
                                 url_params: dict,
                                 auth_type: AuthType,
                                 auth_scope: List[Union[AuthScope, List[AuthScope]]],
                                 return_type: Type[T],
                                 body_data: Optional[dict] = None,
                                 split_lists: bool = False,
                                 iter_field: str = 'data',
                                 in_data: bool = False):
        _url = build_url(self.base_url + url, url_params, remove_none=True, split_lists=split_lists)
        async with ClientSession(timeout=self.session_timeout) as session:
            response = await self._api_request(method, session, _url, auth_type, auth_scope, data=body_data)
            data = await response.json()
        url_params['after'] = data.get('pagination', {}).get('cursor')
        if in_data:
            data = data['data']
        cont_data = {
            'req': self._api_request,
            'method': method,
            'url': self.base_url + url,
            'param': url_params,
            'split': split_lists,
            'auth_t': auth_type,
            'auth_s': auth_scope,
            'body': body_data,
            'iter_field': iter_field,
            'in_data': in_data
        }
        return return_type(cont_data, **data)

    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Type[T],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> T: ...
    
    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Type[dict],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> dict: ...
    
    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Type[Sequence[T]],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> Sequence[T]: ...
    
    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Type[str],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> str: ...
    
    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Type[Sequence[str]],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> Sequence[str]: ...
    
    @overload
    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: None,
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> None: ...

    async def _build_result(self,
                            method: str,
                            url: str,
                            url_params: dict,
                            auth_type: AuthType,
                            auth_scope: List[Union[AuthScope, List[AuthScope]]],
                            return_type: Union[Type[T], None, Type[Sequence[T]], Type[dict], Type[str], Type[Sequence[str]]],
                            body_data: Optional[dict] = None,
                            split_lists: bool = False,
                            get_from_data: bool = True,
                            result_type: ResultType = ResultType.RETURN_TYPE,
                            error_handler: Optional[Mapping[int, BaseException]] = None) -> Union[T, None, int, str, Sequence[T], dict, str, Sequence[str]]:
        async with ClientSession(timeout=self.session_timeout) as session:
            _url = build_url(self.base_url + url, url_params, remove_none=True, split_lists=split_lists)
            response = await self._api_request(method, session, _url, auth_type, auth_scope, data=body_data)
            if error_handler is not None:
                if response.status in error_handler.keys():
                    raise error_handler[response.status]
            if result_type == ResultType.STATUS_CODE:
                return response.status
            if result_type == ResultType.TEXT:
                return await response.text()
            if return_type is not None:
                data = await response.json()
                if isinstance(return_type, dict):
                    return data
                origin = return_type.__origin__ if hasattr(return_type, '__origin__') else None # type: ignore
                if origin is list:
                    c = return_type.__args__[0] # type: ignore
                    return [x if isinstance(x, c) else c(**x) for x in data['data']]
                if get_from_data:
                    d = data['data']
                    if isinstance(d, list):
                        if len(d) == 0:
                            return None
                        return return_type(**d[0])
                    else:
                        return return_type(**d)
                else:
                    return return_type(**data)
            return None

    async def _generate_app_token(self) -> None:
        if self.app_secret is None:
            raise MissingAppSecretException()
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'client_credentials',
            'scope': build_scope(self._app_auth_scope)
        }
        self.logger.debug('generating fresh app token')
        url = build_url(self.auth_base_url + 'token', params)
        async with ClientSession(timeout=self.session_timeout) as session:
            result = await session.post(url)
        if result.status != 200:
            raise TwitchAuthorizationException(f'Authentication failed with code {result.status} ({result.text})')
        try:
            data = await result.json()
            self._app_auth_token = data['access_token']
        except ValueError:
            raise TwitchAuthorizationException('Authentication response did not have a valid json body')
        except KeyError:
            raise TwitchAuthorizationException('Authentication response did not contain access_token')

    async def authenticate_app(self, scope: List[AuthScope]) -> None:
        """Authenticate with a fresh generated app token

        :param scope: List of Authorization scopes to use
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the authentication fails
        :return: None
        """
        self._app_auth_scope = scope
        await self._generate_app_token()
        self._has_app_auth = True

    async def set_app_authentication(self, token: str, scope: List[AuthScope]):
        """Set a app token, most likely only used for testing purposes

        :param token: the app token
        :param scope: List of Authorization scopes that the given app token has
        """
        self._app_auth_token = token
        self._app_auth_scope = scope
        self._has_app_auth = True

    async def set_user_authentication(self,
                                      token: str,
                                      scope: List[AuthScope],
                                      refresh_token: Optional[str] = None,
                                      validate: bool = True):
        """Set a user token to be used.

        :param token: the generated user token
        :param scope: List of Authorization Scopes that the given user token has
        :param refresh_token: The generated refresh token, has to be provided if :attr:`auto_refresh_auth` is True |default| :code:`None`
        :param validate: if true, validate the set token for being a user auth token and having the required scope |default| :code:`True`
        :raises ValueError: if :attr:`auto_refresh_auth` is True but refresh_token is not set
        :raises ~twitchAPI.type.MissingScopeException: if given token is missing one of the required scopes
        :raises ~twitchAPI.type.InvalidTokenException: if the given token is invalid or for a different client id
        """
        if refresh_token is None and self.auto_refresh_auth:
            raise ValueError('refresh_token has to be provided when auto_refresh_auth is True')
        if scope is None:
            raise MissingScopeException('scope was not provided')
        if validate:
            from .oauth import validate_token, refresh_access_token
            val_result = await validate_token(token, auth_base_url=self.auth_base_url)
            if val_result.get('status', 200) == 401 and refresh_token is not None:
                # try to refresh once and revalidate
                token, refresh_token = await refresh_access_token(refresh_token, self.app_id, self.app_secret, auth_base_url=self.auth_base_url) # type: ignore
                if self.user_auth_refresh_callback is not None:
                    await self.user_auth_refresh_callback(token, refresh_token) # type: ignore
                val_result = await validate_token(token, auth_base_url=self.auth_base_url)
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

        self._user_auth_token = token
        self._user_auth_refresh_token = refresh_token
        self._user_auth_scope = scope
        self._has_user_auth = True

    def get_app_token(self) -> Union[str, None]:
        """Returns the app token that the api uses or None when not authenticated.

        :return: app token
        """
        return self._app_auth_token

    def get_user_auth_token(self) -> Union[str, None]:
        """Returns the current user auth token, None if no user Authentication is set

        :return: current user auth token
        """
        return self._user_auth_token

    async def get_refreshed_user_auth_token(self) -> Union[str, None]:
        """Validates the current set user auth token and returns it

        Will reauth if token is invalid
        """
        if self._user_auth_token is None:
            return None
        from .oauth import validate_token
        val_result = await validate_token(self._user_auth_token, auth_base_url=self.auth_base_url)
        if val_result.get('status', 200) != 200:
            # refresh token
            await self.refresh_used_token()
        return self._user_auth_token

    async def get_refreshed_app_token(self) -> Optional[str]:
        if self._app_auth_token is None:
            return None
        from .oauth import validate_token
        val_result = await validate_token(self._app_auth_token, auth_base_url=self.auth_base_url)
        if val_result.get('status', 200) != 200:
            await self._refresh_app_token()
        return self._app_auth_token

    def get_used_token(self) -> Union[str, None]:
        """Returns the currently used token, can be either the app or user auth Token or None if no auth is set

        :return: the currently used auth token or None if no Authentication is set
        """
        # if no auth is set, self.__app_auth_token will be None
        return self._user_auth_token if self._has_user_auth else self._app_auth_token

    # ======================================================================================================================
    # API calls
    # ======================================================================================================================

    async def get_extension_analytics(self,
                                      after: Optional[str] = None,
                                      extension_id: Optional[str] = None,
                                      first: int = 20,
                                      ended_at: Optional[datetime] = None,
                                      started_at: Optional[datetime] = None,
                                      report_type: Optional[AnalyticsReportType] = None) -> AsyncGenerator[ExtensionAnalytic, None]:
        """Gets a URL that extension developers can use to download analytics reports (CSV files) for their extensions.
        The URL is valid for 5 minutes.\n\n

        Requires User authentication with scope :py:const:`~twitchAPI.type.AuthScope.ANALYTICS_READ_EXTENSION`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-extension-analytics

        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param extension_id: If this is specified, the returned URL points to an analytics report for just the
                    specified extension. |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param ended_at: Ending date/time for returned reports, if this is provided, `started_at` must also be specified. |default| :code:`None`
        :param started_at: Starting date/time for returned reports, if this is provided, `ended_at` must also be specified. |default| :code:`None`
        :param report_type: Type of analytics report that is returned |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the extension specified in extension_id was not found
        :raises ValueError: When you only supply `started_at` or `ended_at` without the other or when first is not in range 1 to 100
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
        async for y in self._build_generator('GET', 'analytics/extensions', url_params, AuthType.USER,
                                             [AuthScope.ANALYTICS_READ_EXTENSION], ExtensionAnalytic):
            yield y

    async def get_game_analytics(self,
                                 after: Optional[str] = None,
                                 first: int = 20,
                                 game_id: Optional[str] = None,
                                 ended_at: Optional[datetime] = None,
                                 started_at: Optional[datetime] = None,
                                 report_type: Optional[AnalyticsReportType] = None) -> AsyncGenerator[GameAnalytics, None]:
        """Gets a URL that game developers can use to download analytics reports (CSV files) for their games.
        The URL is valid for 5 minutes.\n\n

        Requires User authentication with scope :py:const:`~twitchAPI.type.AuthScope.ANALYTICS_READ_GAMES`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-game-analytics

        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param game_id: Game ID |default| :code:`None`
        :param ended_at: Ending date/time for returned reports, if this is provided, `started_at` must also be specified. |default| :code:`None`
        :param started_at: Starting date/time for returned reports, if this is provided, `ended_at` must also be specified. |default| :code:`None`
        :param report_type: Type of analytics report that is returned. |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the game specified in game_id was not found
        :raises ValueError: When you only supply `started_at` or `ended_at` without the other or when first is not in range 1 to 100
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
            'type': report_type
        }
        async for y in self._build_generator('GET', 'analytics/game', url_params, AuthType.USER, [AuthScope.ANALYTICS_READ_GAMES], GameAnalytics):
            yield y

    async def get_creator_goals(self, broadcaster_id: str) -> AsyncGenerator[CreatorGoal, None]:
        """Gets Creator Goal Details for the specified channel.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_GOALS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-creator-goals

        :param broadcaster_id: The ID of the broadcaster that created the goals.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        async for y in self._build_generator('GET', 'goals', {'broadcaster_id': broadcaster_id}, AuthType.USER,
                                             [AuthScope.CHANNEL_READ_GOALS], CreatorGoal):
            yield y

    async def get_bits_leaderboard(self,
                                   count: Optional[int] = 10,
                                   period: Optional[TimePeriod] = TimePeriod.ALL,
                                   started_at: Optional[datetime] = None,
                                   user_id: Optional[str] = None) -> BitsLeaderboard:
        """Gets a ranked list of Bits leaderboard information for an authorized broadcaster.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.BITS_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-bits-leaderboard

        :param count: Number of results to be returned. In range 1 to 100, |default| :code:`10`
        :param period: Time period over which data is aggregated, |default| :const:`twitchAPI.types.TimePeriod.ALL`
        :param started_at: Timestamp for the period over which the returned data is aggregated. |default| :code:`None`
        :param user_id: ID of the user whose results are returned; i.e., the person who paid for the Bits. |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if count is not None and (count > 100 or count < 1):
            raise ValueError('count must be between 1 and 100')
        url_params = {
            'count': count,
            'period': period.value if period is not None else None,
            'started_at': datetime_to_str(started_at),
            'user_id': user_id
        }
        return await self._build_result('GET', 'bits/leaderboard', url_params, AuthType.USER, [AuthScope.BITS_READ], BitsLeaderboard,
                                        get_from_data=False)

    async def get_extension_transactions(self,
                                         extension_id: str,
                                         transaction_id: Optional[Union[str, List[str]]] = None,
                                         after: Optional[str] = None,
                                         first: int = 20) -> AsyncGenerator[ExtensionTransaction, None]:
        """Get Extension Transactions allows extension back end servers to fetch a list of transactions that have
        occurred for their extension across all of Twitch.
        A transaction is a record of a user exchanging Bits for an in-Extension digital good.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-extension-transactions

        :param extension_id: ID of the extension to list transactions for.
        :param transaction_id: Transaction IDs to look up. Can either be a list of str or str |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if one or more transaction IDs specified in transaction_id where not found
        :raises ValueError: if first is not in range 1 to 100
        :raises ValueError: if transaction_ids is longer than 100 entries
        """
        if first > 100 or first < 1:
            raise ValueError("first must be between 1 and 100")
        if transaction_id is not None and isinstance(transaction_id, list) and len(transaction_id) > 100:
            raise ValueError("transaction_ids can't be longer than 100 entries")
        url_param = {
            'extension_id': extension_id,
            'id': transaction_id,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'extensions/transactions', url_param, AuthType.EITHER, [], ExtensionTransaction):
            yield y

    async def get_chat_settings(self,
                                broadcaster_id: str,
                                moderator_id: Optional[str] = None) -> ChatSettings:
        """Gets the broadcaster’s chat settings.

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-chat-settings

        :param broadcaster_id: The ID of the broadcaster whose chat settings you want to get
        :param moderator_id: Required only to access the non_moderator_chat_delay or non_moderator_chat_delay_duration settings |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        url_param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        return await self._build_result('GET', 'chat/settings', url_param, AuthType.EITHER, [], ChatSettings)

    async def update_chat_settings(self,
                                   broadcaster_id: str,
                                   moderator_id: str,
                                   emote_mode: Optional[bool] = None,
                                   follower_mode: Optional[bool] = None,
                                   follower_mode_duration: Optional[int] = None,
                                   non_moderator_chat_delay: Optional[bool] = None,
                                   non_moderator_chat_delay_duration: Optional[int] = None,
                                   slow_mode: Optional[bool] = None,
                                   slow_mode_wait_time: Optional[int] = None,
                                   subscriber_mode: Optional[bool] = None,
                                   unique_chat_mode: Optional[bool] = None) -> ChatSettings:
        """Updates the broadcaster’s chat settings.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-chat-settings

        :param broadcaster_id: The ID of the broadcaster whose chat settings you want to update.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
        :param emote_mode: A Boolean value that determines whether chat messages must contain only emotes. |default| :code:`None`
        :param follower_mode: A Boolean value that determines whether the broadcaster restricts the chat room to
                    followers only, based on how long they’ve followed. |default| :code:`None`
        :param follower_mode_duration: The length of time, in minutes, that the followers must have followed the
                    broadcaster to participate in the chat room |default| :code:`None`
        :param non_moderator_chat_delay: A Boolean value that determines whether the broadcaster adds a short delay
                    before chat messages appear in the chat room. |default| :code:`None`
        :param non_moderator_chat_delay_duration: he amount of time, in seconds, that messages are delayed
                    from appearing in chat. Possible Values: 2, 4 and 6 |default| :code:`None`
        :param slow_mode: A Boolean value that determines whether the broadcaster limits how often users in the
                    chat room are allowed to send messages. |default| :code:`None`
        :param slow_mode_wait_time: The amount of time, in seconds, that users need to wait between sending messages |default| :code:`None`
        :param subscriber_mode: A Boolean value that determines whether only users that subscribe to the
                    broadcaster’s channel can talk in the chat room. |default| :code:`None`
        :param unique_chat_mode: A Boolean value that determines whether the broadcaster requires users to post
                    only unique messages in the chat room. |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if non_moderator_chat_delay_duration is not one of 2, 4 or 6
        """
        if non_moderator_chat_delay_duration is not None:
            if non_moderator_chat_delay_duration not in (2, 4, 6):
                raise ValueError('non_moderator_chat_delay_duration has to be one of 2, 4 or 6')
        url_param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        body = remove_none_values({
            'emote_mode': emote_mode,
            'follower_mode': follower_mode,
            'follower_mode_duration': follower_mode_duration,
            'non_moderator_chat_delay': non_moderator_chat_delay,
            'non_moderator_chat_delay_duration': non_moderator_chat_delay_duration,
            'slow_mode': slow_mode,
            'slow_mode_wait_time': slow_mode_wait_time,
            'subscriber_mode': subscriber_mode,
            'unique_chat_mode': unique_chat_mode
        })
        return await self._build_result('PATCH', 'chat/settings', url_param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS],
                                        ChatSettings, body_data=body)

    async def create_clip(self,
                          broadcaster_id: str,
                          has_delay: bool = False) -> CreatedClip:
        """Creates a clip programmatically. This returns both an ID and an edit URL for the new clip.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.CLIPS_EDIT`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-clip

        :param broadcaster_id: Broadcaster ID of the stream from which the clip will be made.
        :param has_delay: If False, the clip is captured from the live stream when the API is called; otherwise,
                a delay is added before the clip is captured (to account for the brief delay between the broadcaster’s
                stream and the viewer’s experience of that stream). |default| :code:`False`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster is not live
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'has_delay': has_delay
        }
        errors = {403: TwitchAPIException('The broadcaster has restricted the ability to capture clips to followers and/or subscribers only or the'
                                          'specified broadcaster has not enabled clips on their channel.')}
        return await self._build_result('POST', 'clips', param, AuthType.USER, [AuthScope.CLIPS_EDIT], CreatedClip, error_handler=errors)

    async def get_clips(self,
                        broadcaster_id: Optional[str] = None,
                        game_id: Optional[str] = None,
                        clip_id: Optional[List[str]] = None,
                        is_featured: Optional[bool] = None,
                        after: Optional[str] = None,
                        before: Optional[str] = None,
                        ended_at: Optional[datetime] = None,
                        started_at: Optional[datetime] = None,
                        first: int = 20) -> AsyncGenerator[Clip, None]:
        """Gets clip information by clip ID (one or more), broadcaster ID (one only), or game ID (one only).
        Clips are returned sorted by view count, in descending order.\n\n

        Requires App or User authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-clips

        :param broadcaster_id: ID of the broadcaster for whom clips are returned. |default| :code:`None`
        :param game_id: ID of the game for which clips are returned. |default| :code:`None`
        :param clip_id: ID of the clip being queried. Limit: 100. |default| :code:`None`
        :param is_featured: A Boolean value that determines whether the response includes featured clips. |br|
                     If :code:`True`, returns only clips that are featured. |br|
                     If :code:`False`, returns only clips that aren’t featured. |br|
                     If :code:`None`, all clips are returned. |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param ended_at: Ending date/time for returned clips |default| :code:`None`
        :param started_at: Starting date/time for returned clips |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if you try to query more than 100 clips in one call
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ValueError: if not exactly one of clip_id, broadcaster_id or game_id is given
        :raises ValueError: if first is not in range 1 to 100
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the game specified in game_id was not found
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
            'started_at': datetime_to_str(started_at),
            'is_featured': is_featured
        }
        async for y in self._build_generator('GET', 'clips', param, AuthType.EITHER, [], Clip, split_lists=True):
            yield y

    async def get_top_games(self,
                            after: Optional[str] = None,
                            before: Optional[str] = None,
                            first: int = 20) -> AsyncGenerator[Game, None]:
        """Gets games sorted by number of current viewers on Twitch, most popular first.\n\n

        Requires App or User authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-top-games

        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if first < 1 or first > 100:
            raise ValueError('first must be between 1 and 100')
        param = {
            'after': after,
            'before': before,
            'first': first
        }
        async for y in self._build_generator('GET', 'games/top', param, AuthType.EITHER, [], Game):
            yield y

    async def get_games(self,
                        game_ids: Optional[List[str]] = None,
                        names: Optional[List[str]] = None,
                        igdb_ids: Optional[List[str]] = None) -> AsyncGenerator[Game, None]:
        """Gets game information by game ID or name.\n\n

        Requires User or App authentication.
        In total, only 100 game ids and names can be fetched at once.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-games

        :param game_ids: Game ID |default| :code:`None`
        :param names: Game Name |default| :code:`None`
        :param igdb_ids: IGDB ID |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if none of game_ids, names or igdb_ids are given or if game_ids, names and igdb_ids are more than 100 entries combined.
        """
        if game_ids is None and names is None and igdb_ids is None:
            raise ValueError('at least one of game_ids, names or igdb_ids has to be set')
        if (len(game_ids) if game_ids is not None else 0) + \
                (len(names) if names is not None else 0) + \
                (len(igdb_ids) if igdb_ids is not None else 0) > 100:
            raise ValueError('in total, only 100 game_ids, names and igdb_ids can be passed')
        param = {
            'id': game_ids,
            'name': names,
            'igdb_id': igdb_ids
        }
        async for y in self._build_generator('GET', 'games', param, AuthType.EITHER, [], Game, split_lists=True):
            yield y

    async def check_automod_status(self,
                                   broadcaster_id: str,
                                   automod_check_entries: List[AutoModCheckEntry]) -> AsyncGenerator[AutoModStatus, None]:
        """Determines whether a string message meets the channel’s AutoMod requirements.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#check-automod-status

        :param broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param automod_check_entries: The Automod Check Entries
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        body = {'data': automod_check_entries}
        async for y in self._build_generator('POST', 'moderation/enforcements/status', {'broadcaster_id': broadcaster_id},
                                             AuthType.USER, [AuthScope.MODERATION_READ], AutoModStatus, body_data=body):
            yield y

    async def get_automod_settings(self,
                                   broadcaster_id: str,
                                   moderator_id: str) -> AutoModSettings:
        """Gets the broadcaster’s AutoMod settings.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_AUTOMOD_SETTINGS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-automod-settings

        :param broadcaster_id: The ID of the broadcaster whose AutoMod settings you want to get.
        :param moderator_id: The ID of the broadcaster or a user that has permission to moderate the broadcaster’s chat room.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": moderator_id
        }
        error_handler = {403: TwitchAPIException('Forbidden: The user in moderator_id is not one of the broadcaster\'s moderators.')}
        return await self._build_result('GET',
                                        'moderation/automod/settings',
                                        param,
                                        AuthType.USER,
                                        [AuthScope.MODERATOR_READ_AUTOMOD_SETTINGS],
                                        AutoModSettings,
                                        error_handler=error_handler)

    async def update_automod_settings(self,
                                      broadcaster_id: str,
                                      moderator_id: str,
                                      settings: Optional[AutoModSettings] = None,
                                      overall_level: Optional[int] = None) -> AutoModSettings:
        """Updates the broadcaster’s AutoMod settings.

        You can either set the individual level or the overall level, but not both at the same time.
        Setting the overall_level parameter in settings will be ignored.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_AUTOMOD_SETTINGS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-automod-settings

        :param broadcaster_id: The ID of the broadcaster whose AutoMod settings you want to update.
        :param moderator_id: The ID of the broadcaster or a user that has permission to moderate the broadcaster’s chat room.
        :param settings: If you want to change individual settings, set this. |default|:code:`None`
        :param overall_level: If you want to change the overall level, set this. |default|:code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if both settings and overall_level are given or none of them are given
        """
        if (settings is not None and overall_level is not None) or (settings is None and overall_level is None):
            raise ValueError('You have to specify exactly one of settings or oevrall_level')
        param = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": moderator_id
        }
        body = settings.to_dict() if settings is not None else {}
        body['overall_level'] = overall_level
        return await self._build_result('PUT',
                                        'moderation/automod/settings',
                                        param,
                                        AuthType.USER,
                                        [AuthScope.MODERATOR_MANAGE_AUTOMOD_SETTINGS],
                                        AutoModSettings,
                                        body_data=remove_none_values(body))

    async def get_banned_users(self,
                               broadcaster_id: str,
                               user_id: Optional[str] = None,
                               after: Optional[str] = None,
                               first: Optional[int] = 20,
                               before: Optional[str] = None) -> AsyncGenerator[BannedUser, None]:
        """Returns all banned and timed-out users in a channel.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-banned-users

        :param broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param user_id: Filters the results and only returns a status object for users who are banned in this
                        channel and have a matching user_id. |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id,
            'after': after,
            'first': first,
            'before': before
        }
        async for y in self._build_generator('GET', 'moderation/banned', param, AuthType.USER, [AuthScope.MODERATION_READ], BannedUser):
            yield y

    async def ban_user(self,
                       broadcaster_id: str,
                       moderator_id: str,
                       user_id: str,
                       reason: str,
                       duration: Optional[int] = None) -> BanUserResponse:
        """Bans a user from participating in a broadcaster’s chat room, or puts them in a timeout.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BANNED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#ban-user

        :param broadcaster_id: The ID of the broadcaster whose chat room the user is being banned from.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room. This ID must match the user ID
                    associated with the user OAuth token.
        :param user_id: The ID of the user to ban or put in a timeout.
        :param reason: The reason the user is being banned or put in a timeout. The text is user defined and limited to a maximum of 500 characters.
        :param duration: To ban a user indefinitely, don't set this. Put a user in timeout for the number of seconds specified.
                    Maximum 1_209_600 (2 weeks) |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if duration is set and not between 1 and 1_209_600
        :raises ValueError: if reason is not between 1 and 500 characters in length
        """
        if duration is not None and (duration < 1 or duration > 1_209_600):
            raise ValueError('duration must be either omitted or between 1 and 1209600')
        if len(reason) < 1 or len(reason) > 500:
            raise ValueError('reason must be between 1 and 500 characters in length')
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        body = {
            'data': remove_none_values({
                'duration': duration,
                'reason': reason,
                'user_id': user_id
            })
        }
        return await self._build_result('POST', 'moderation/bans', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_BANNED_USERS], BanUserResponse,
                                        body_data=body, get_from_data=True)

    async def unban_user(self,
                         broadcaster_id: str,
                         moderator_id: str,
                         user_id: str) -> bool:
        """Removes the ban or timeout that was placed on the specified user

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BANNED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#unban-user

        :param broadcaster_id: The ID of the broadcaster whose chat room the user is banned from chatting in.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
                    This ID must match the user ID associated with the user OAuth token.
        :param user_id: The ID of the user to remove the ban or timeout from.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id,
            'user_id': user_id
        }
        return await self._build_result('DELETE', 'moderation/bans', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_BANNED_USERS], None,
                                        result_type=ResultType.STATUS_CODE) == 204

    async def get_blocked_terms(self,
                                broadcaster_id: str,
                                moderator_id: str,
                                after: Optional[str] = None,
                                first: Optional[int] = None) -> AsyncGenerator[BlockedTerm, None]:
        """Gets the broadcaster’s list of non-private, blocked words or phrases.
        These are the terms that the broadcaster or moderator added manually, or that were denied by AutoMod.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_BLOCKED_TERMS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-blocked-terms

        :param broadcaster_id: The ID of the broadcaster whose blocked terms you’re getting.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
                    This ID must match the user ID associated with the user OAuth token.
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is set and not between 1 and 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be between 1 and 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id,
            'first': first,
            'after': after
        }
        async for y in self._build_generator('GET', 'moderation/blocked_terms', param, AuthType.USER, [AuthScope.MODERATOR_READ_BLOCKED_TERMS],
                                             BlockedTerm):
            yield y

    async def add_blocked_term(self,
                               broadcaster_id: str,
                               moderator_id: str,
                               text: str) -> BlockedTerm:
        """Adds a word or phrase to the broadcaster’s list of blocked terms. These are the terms that broadcasters don’t want used in their chat room.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#add-blocked-term

        :param broadcaster_id: The ID of the broadcaster that owns the list of blocked terms.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
                    This ID must match the user ID associated with the user OAuth token.
        :param text: The word or phrase to block from being used in the broadcaster’s chat room. Between 2 and 500 characters long
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if text is not between 2 and 500 characters long
        """
        if len(text) < 2 or len(text) > 500:
            raise ValueError('text must have a length between 2 and 500 characters')
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        body = {'text': text}
        return await self._build_result('POST', 'moderation/blocked_terms', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS],
                                        BlockedTerm, body_data=body)

    async def remove_blocked_term(self,
                                  broadcaster_id: str,
                                  moderator_id: str,
                                  term_id: str) -> bool:
        """Removes the word or phrase that the broadcaster is blocking users from using in their chat room.

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#remove-blocked-term

        :param broadcaster_id: The ID of the broadcaster that owns the list of blocked terms.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
                        This ID must match the user ID associated with the user OAuth token.
        :param term_id: The ID of the blocked term you want to delete.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id,
            'id': term_id
        }
        return await self._build_result('DELETE', 'moderation/blocked_terms', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS],
                                        None, result_type=ResultType.STATUS_CODE) == 204

    async def get_moderators(self,
                             broadcaster_id: str,
                             user_ids: Optional[List[str]] = None,
                             first: Optional[int] = 20,
                             after: Optional[str] = None) -> AsyncGenerator[Moderator, None]:
        """Returns all moderators in a channel.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.MODERATION_READ`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-moderators

        :param broadcaster_id: Provided broadcaster ID must match the user ID in the user auth token.
        :param user_ids: Filters the results and only returns a status object for users who are moderator in
                        this channel and have a matching user_id. Maximum 100 |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if user_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        if user_ids is not None and len(user_ids) > 100:
            raise ValueError('user_ids can only be 100 entries long')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'first': first,
            'after': after
        }
        async for y in self._build_generator('GET', 'moderation/moderators', param, AuthType.USER, [AuthScope.MODERATION_READ], Moderator,
                                             split_lists=True):
            yield y

    async def create_stream_marker(self,
                                   user_id: str,
                                   description: Optional[str] = None) -> CreateStreamMarkerResponse:
        """Creates a marker in the stream of a user specified by user ID.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-stream-marker

        :param user_id: ID of the broadcaster in whose live stream the marker is created.
        :param description: Description of or comments on the marker. Max length is 140 characters. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if description has more than 140 characters
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the user in user_id is not live, the ID is not valid or has not enabled VODs
        """
        if description is not None and len(description) > 140:
            raise ValueError('max length for description is 140')
        body = {'user_id': user_id}
        if description is not None:
            body['description'] = description
        return await self._build_result('POST', 'streams/markers', {}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_BROADCAST],
                                        CreateStreamMarkerResponse, body_data=body)

    async def get_streams(self,
                          after: Optional[str] = None,
                          before: Optional[str] = None,
                          first: int = 20,
                          game_id: Optional[List[str]] = None,
                          language: Optional[List[str]] = None,
                          user_id: Optional[List[str]] = None,
                          user_login: Optional[List[str]] = None,
                          stream_type: Optional[str] = None) -> AsyncGenerator[Stream, None]:
        """Gets information about active streams. Streams are returned sorted by number of current viewers, in
        descending order. Across multiple pages of results, there may be duplicate or missing streams, as viewers join
        and leave streams.\n\n

        Requires App or User authentication.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-streams

        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param game_id: Returns streams broadcasting a specified game ID. You can specify up to 100 IDs. |default| :code:`None`
        :param language: Stream language. You can specify up to 100 languages. |default| :code:`None`
        :param user_id: Returns streams broadcast by one or more specified user IDs. You can specify up to 100 IDs. |default| :code:`None`
        :param user_login: Returns streams broadcast by one or more specified user login names.
                        You can specify up to 100 names. |default| :code:`None`
        :param stream_type: The type of stream to filter the list of streams by. Possible values are :code:`all` and :code:`live`
                        |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or one of the following fields have more than 100 entries:
                        `user_id, game_id, language, user_login`
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
            'user_login': user_login,
            'type': stream_type
        }
        async for y in self._build_generator('GET', 'streams', param, AuthType.EITHER, [], Stream, split_lists=True):
            yield y

    async def get_stream_markers(self,
                                 user_id: str,
                                 video_id: str,
                                 after: Optional[str] = None,
                                 before: Optional[str] = None,
                                 first: int = 20) -> AsyncGenerator[GetStreamMarkerResponse, None]:
        """Gets a list of markers for either a specified user’s most recent stream or a specified VOD/video (stream),
        ordered by recency.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-stream-markers

        Only one of user_id and video_id must be specified.

        :param user_id: ID of the broadcaster from whose stream markers are returned.
        :param video_id: ID of the VOD/video whose stream markers are returned.
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100 or neither user_id nor video_id is provided
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the user specified in user_id does not have videos
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
        async for y in self._build_generator('GET', 'streams/markers', param, AuthType.USER, [AuthScope.USER_READ_BROADCAST],
                                             GetStreamMarkerResponse):
            yield y

    async def get_broadcaster_subscriptions(self,
                                            broadcaster_id: str,
                                            user_ids: Optional[List[str]] = None,
                                            after: Optional[str] = None,
                                            first: Optional[int] = 20) -> BroadcasterSubscriptions:
        """Get all of a broadcaster’s subscriptions.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_SUBSCRIPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-broadcaster-subscriptions

        :param broadcaster_id: User ID of the broadcaster. Must match the User ID in the Bearer token.
        :param user_ids: Unique identifier of account to get subscription status of. Maximum 100 entries |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if user_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        if user_ids is not None and len(user_ids) > 100:
            raise ValueError('user_ids can have a maximum of 100 entries')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'first': first,
            'after': after
        }
        return await self._build_iter_result('GET', 'subscriptions', param, AuthType.USER, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS],
                                             BroadcasterSubscriptions, split_lists=True)

    async def check_user_subscription(self,
                                      broadcaster_id: str,
                                      user_id: str) -> UserSubscription:
        """Checks if a specific user (user_id) is subscribed to a specific channel (broadcaster_id).

        Requires User or App Authorization with scope :const:`~twitchAPI.type.AuthScope.USER_READ_SUBSCRIPTIONS`

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#check-user-subscription

        :param broadcaster_id: User ID of an Affiliate or Partner broadcaster.
        :param user_id: User ID of a Twitch viewer.
        :raises ~twitchAPI.type.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the app or user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if user is not subscribed to the given broadcaster
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id
        }
        return await self._build_result('GET', 'subscriptions/user', param, AuthType.EITHER, [AuthScope.USER_READ_SUBSCRIPTIONS], UserSubscription)

    async def get_channel_teams(self,
                                broadcaster_id: str) -> Sequence[ChannelTeam]:
        """Retrieves a list of Twitch Teams of which the specified channel/broadcaster is a member.\n\n

        Requires User or App authentication.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference/#get-channel-teams

        :param broadcaster_id: User ID for a Twitch user.
        :raises ~twitchAPI.type.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster was not found or is not member of a team
        """
        return await self._build_result('GET', 'teams/channel', {'broadcaster_id': broadcaster_id}, AuthType.EITHER, [], List[ChannelTeam])

    async def get_teams(self,
                        team_id: Optional[str] = None,
                        name: Optional[str] = None) -> ChannelTeam:
        """Gets information for a specific Twitch Team.\n\n

        Requires User or App authentication.
        One of the two optional query parameters must be specified.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference/#get-teams

        :param team_id: Team ID |default| :code:`None`
        :param name: Team Name |default| :code:`None`
        :raises ~twitchAPI.type.UnauthorizedException: if app or user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if neither team_id nor name are given or if both team_id and names are given.
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the specified team was not found
        """
        if team_id is None and name is None:
            raise ValueError('You need to specify one of the two optional parameter.')
        if team_id is not None and name is not None:
            raise ValueError('Only one optional parameter must be specified.')
        param = {
            'id': team_id,
            'name': name
        }
        return await self._build_result('GET', 'teams', param, AuthType.EITHER, [], ChannelTeam)

    async def get_users(self,
                        user_ids: Optional[List[str]] = None,
                        logins: Optional[List[str]] = None) -> AsyncGenerator[TwitchUser, None]:
        """Gets information about one or more specified Twitch users.
        Users are identified by optional user IDs and/or login name.
        If neither a user ID nor a login name is specified, the user is the one authenticated.\n\n

        Requires App authentication if either user_ids or logins is provided, otherwise requires a User authentication.
        If you have user Authentication and want to get your email info, you also need the authentication scope
        :const:`~twitchAPI.type.AuthScope.USER_READ_EMAIL`\n
        If you provide user_ids and/or logins, the maximum combined entries should not exceed 100.

        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-users

        :param user_ids: User ID. Multiple user IDs can be specified. Limit: 100. |default| :code:`None`
        :param logins: User login name. Multiple login names can be specified. Limit: 100. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if more than 100 combined user_ids and logins where provided
        """
        if (len(user_ids) if user_ids is not None else 0) + (len(logins) if logins is not None else 0) > 100:
            raise ValueError('the total number of entries in user_ids and logins can not be more than 100')
        url_params = {
            'id': user_ids,
            'login': logins
        }
        at = AuthType.USER if (user_ids is None or len(user_ids) == 0) and (logins is None or len(logins) == 0) else AuthType.EITHER
        async for f in self._build_generator('GET', 'users', url_params, at, [], TwitchUser, split_lists=True):
            yield f

    async def get_channel_followers(self,
                                    broadcaster_id: str,
                                    user_id: Optional[str] = None,
                                    first: Optional[int] = None,
                                    after: Optional[str] = None) -> ChannelFollowersResult:
        """ Gets a list of users that follow the specified broadcaster.
        You can also use this endpoint to see whether a specific user follows the broadcaster.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_FOLLOWERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-followers

        .. note:: This can also be used without the required scope or just with App Authentication, but the result will only include the total number
                  of followers in these cases.

        :param broadcaster_id: The broadcaster’s ID. Returns the list of users that follow this broadcaster.
        :param user_id: A user’s ID. Use this parameter to see whether the user follows this broadcaster.
            If specified, the response contains this user if they follow the broadcaster.
            If not specified, the response contains all users that follow the broadcaster. |default|:code:`None`
        :param first: The maximum number of items to return per API call.
                    You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                    fetch the amount of results you desire.\n
                    Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id,
            'first': first,
            'after': after
        }
        return await self._build_iter_result('GET', 'channels/followers', param, AuthType.EITHER, [], ChannelFollowersResult)

    async def get_followed_channels(self,
                                    user_id: str,
                                    broadcaster_id: Optional[str] = None,
                                    first: Optional[int] = None,
                                    after: Optional[str] = None) -> FollowedChannelsResult:
        """Gets a list of broadcasters that the specified user follows.
        You can also use this endpoint to see whether a user follows a specific broadcaster.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_READ_FOLLOWS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-followed-channels

        :param user_id: A user’s ID. Returns the list of broadcasters that this user follows. This ID must match the user ID in the user OAuth token.
        :param broadcaster_id: A broadcaster’s ID. Use this parameter to see whether the user follows this broadcaster.
            If specified, the response contains this broadcaster if the user follows them.
            If not specified, the response contains all broadcasters that the user follows. |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        param = {
            'user_id': user_id,
            'broadcaster_id': broadcaster_id,
            'first': first,
            'after': after
        }
        return await self._build_iter_result('GET', 'channels/followed', param, AuthType.USER, [AuthScope.USER_READ_FOLLOWS], FollowedChannelsResult)

    async def update_user(self,
                          description: str) -> TwitchUser:
        """Updates the description of the Authenticated user.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.USER_EDIT`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-user

        :param description: User’s account description
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        return await self._build_result('PUT', 'users', {'description': description}, AuthType.USER, [AuthScope.USER_EDIT], TwitchUser)

    async def get_user_extensions(self) -> Sequence[UserExtension]:
        """Gets a list of all extensions (both active and inactive) for the authenticated user\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-extensions

        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        return await self._build_result('GET', 'users/extensions/list', {}, AuthType.USER, [AuthScope.USER_READ_BROADCAST], List[UserExtension])

    async def get_user_active_extensions(self,
                                         user_id: Optional[str] = None) -> UserActiveExtensions:
        """Gets information about active extensions installed by a specified user, identified by a user ID or the
        authenticated user.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.USER_READ_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-active-extensions

        :param user_id: ID of the user whose installed extensions will be returned. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        return await self._build_result('GET', 'users/extensions', {'user_id': user_id}, AuthType.USER, [AuthScope.USER_READ_BROADCAST],
                                        UserActiveExtensions)

    async def update_user_extensions(self,
                                     data: UserActiveExtensions) -> UserActiveExtensions:
        """"Updates the activation state, extension ID, and/or version number of installed extensions
        for the authenticated user.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.USER_EDIT_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-user-extensions

        :param data: The user extension data to be written
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the extension specified in id and version was not found
        """
        dat = {'data': data.to_dict(False)}
        return await self._build_result('PUT', 'users/extensions', {}, AuthType.USER, [AuthScope.USER_EDIT_BROADCAST], UserActiveExtensions,
                                        body_data=dat)

    async def get_videos(self,
                         ids: Optional[List[str]] = None,
                         user_id: Optional[str] = None,
                         game_id: Optional[str] = None,
                         after: Optional[str] = None,
                         before: Optional[str] = None,
                         first: Optional[int] = 20,
                         language: Optional[str] = None,
                         period: TimePeriod = TimePeriod.ALL,
                         sort: SortMethod = SortMethod.TIME,
                         video_type: VideoType = VideoType.ALL) -> AsyncGenerator[Video, None]:
        """Gets video information by video ID (one or more), user ID (one only), or game ID (one only).\n\n

        Requires App authentication.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-videos

        :param ids: ID of the video being queried. Limit: 100. |default| :code:`None`
        :param user_id: ID of the user who owns the video. |default| :code:`None`
        :param game_id: ID of the game the video is of. |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param before: Cursor for backward pagination |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param language: Language of the video being queried. |default| :code:`None`
        :param period: Period during which the video was created. |default| :code:`TimePeriod.ALL`
        :param sort: Sort order of the videos. |default| :code:`SortMethod.TIME`
        :param video_type: Type of video. |default| :code:`VideoType.ALL`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100, ids has more than 100 entries or none of ids, user_id nor game_id is provided.
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the game_id was not found or all IDs in video_id where not found
        """
        if ids is None and user_id is None and game_id is None:
            raise ValueError('you must use either ids, user_id or game_id')
        if first is not None and (first < 1 or first > 100):
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
        async for y in self._build_generator('GET', 'videos', param, AuthType.EITHER, [], Video, split_lists=True):
            yield y

    async def get_channel_information(self,
                                      broadcaster_id: Union[str, List[str]]) -> Sequence[ChannelInformation]:
        """Gets channel information for users.\n\n

        Requires App or user authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-information

        :param broadcaster_id: ID of the channel to be returned, can either be a string or a list of strings with up to 100 entries
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if broadcaster_id is a list and does not have between 1 and 100 entries
        """
        if isinstance(broadcaster_id, list):
            if len(broadcaster_id) < 1 or len(broadcaster_id) > 100:
                raise ValueError('broadcaster_id has to have between 1 and 100 entries')
        return await self._build_result('GET', 'channels', {'broadcaster_id': broadcaster_id}, AuthType.EITHER, [], List[ChannelInformation],
                                        split_lists=True)

    async def modify_channel_information(self,
                                         broadcaster_id: str,
                                         game_id: Optional[str] = None,
                                         broadcaster_language: Optional[str] = None,
                                         title: Optional[str] = None,
                                         delay: Optional[int] = None,
                                         tags: Optional[List[str]] = None,
                                         content_classification_labels: Optional[List[str]] = None,
                                         is_branded_content: Optional[bool] = None) -> bool:
        """Modifies channel information for users.\n\n

        Requires User authentication with scope :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_BROADCAST`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#modify-channel-information

        :param broadcaster_id: ID of the channel to be updated
        :param game_id: The current game ID being played on the channel |default| :code:`None`
        :param broadcaster_language: The language of the channel |default| :code:`None`
        :param title: The title of the stream |default| :code:`None`
        :param delay: Stream delay in seconds. Trying to set this while not being a Twitch Partner will fail! |default| :code:`None`
        :param tags: A list of channel-defined tags to apply to the channel. To remove all tags from the channel, set tags to an empty array.
                |default|:code:`None`
        :param content_classification_labels: List of labels that should be set as the Channel’s CCLs.
        :param is_branded_content: Boolean flag indicating if the channel has branded content.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if none of the following fields are specified: `game_id, broadcaster_language, title`
        :raises ValueError: if title is a empty string
        :raises ValueError: if tags has more than 10 entries
        :raises ValueError: if requested a gaming CCL to channel or used Unallowed CCLs declared for underaged authorized user in a restricted country
        :raises ValueError: if the is_branded_content flag was set too frequently
        """
        if game_id is None and broadcaster_language is None and title is None and tags is None:
            raise ValueError('You need to specify at least one of the optional parameter')
        if title is not None and len(title) == 0:
            raise ValueError("title can't be a empty string")
        if tags is not None and len(tags) > 10:
            raise ValueError('tags can only contain up to 10 items')
        body = {k: v for k, v in {'game_id': game_id,
                                  'broadcaster_language': broadcaster_language,
                                  'title': title,
                                  'delay': delay,
                                  'tags': tags,
                                  'content_classification_labels': content_classification_labels,
                                  'is_branded_content': is_branded_content}.items() if v is not None}
        error_handler = {403: ValueError('Either requested to add gaming CCL to channel or used Unallowed CCLs declared for underaged authorized '
                                         'user in a restricted country'),
                         409: ValueError('tried to set is_branded_content flag too frequently')}
        return await self._build_result('PATCH', 'channels', {'broadcaster_id': broadcaster_id}, AuthType.USER,
                                        [AuthScope.CHANNEL_MANAGE_BROADCAST], None, body_data=body, result_type=ResultType.STATUS_CODE,
                                        error_handler=error_handler) == 204

    async def search_channels(self,
                              query: str,
                              first: Optional[int] = 20,
                              after: Optional[str] = None,
                              live_only: Optional[bool] = False) -> AsyncGenerator[SearchChannelResult, None]:
        """Returns a list of channels (users who have streamed within the past 6 months) that match the query via
        channel name or description either entirely or partially.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#search-channels

        :param query: search query
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param live_only: Filter results for live streams only. |default| :code:`False`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be between 1 and 100')
        param = {'query': query,
                 'first': first,
                 'after': after,
                 'live_only': live_only}
        async for y in self._build_generator('GET', 'search/channels', param, AuthType.EITHER, [], SearchChannelResult):
            yield y

    async def search_categories(self,
                                query: str,
                                first: Optional[int] = 20,
                                after: Optional[str] = None) -> AsyncGenerator[SearchCategoryResult, None]:
        """Returns a list of games or categories that match the query via name either entirely or partially.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#search-categories

        :param query: search query
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be between 1 and 100')
        param = {'query': query,
                 'first': first,
                 'after': after}
        async for y in self._build_generator('GET', 'search/categories', param, AuthType.EITHER, [], SearchCategoryResult):
            yield y

    async def get_stream_key(self,
                             broadcaster_id: str) -> str:
        """Gets the channel stream key for a user.\n\n

        Requires User authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_STREAM_KEY`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-stream-key

        :param broadcaster_id: User ID of the broadcaster
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        data = await self._build_result('GET', 'streams/key', {'broadcaster_id': broadcaster_id}, AuthType.USER, [AuthScope.CHANNEL_READ_STREAM_KEY], dict)
        return data['stream_key']

    async def start_commercial(self,
                               broadcaster_id: str,
                               length: int) -> StartCommercialResult:
        """Starts a commercial on a specified channel.\n\n

        Requires User authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_EDIT_COMMERCIAL`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#start-commercial

        :param broadcaster_id: ID of the channel requesting a commercial
        :param length: Desired length of the commercial in seconds. , one of these: [30, 60, 90, 120, 150, 180]
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster_id was not found
        :raises ValueError: if length is not one of these: :code:`30, 60, 90, 120, 150, 180`
        """
        if length not in [30, 60, 90, 120, 150, 180]:
            raise ValueError('length needs to be one of these: [30, 60, 90, 120, 150, 180]')
        param = {
            'broadcaster_id': broadcaster_id,
            'length': length
        }
        return await self._build_result('POST', 'channels/commercial', param, AuthType.USER, [AuthScope.CHANNEL_EDIT_COMMERCIAL],
                                        StartCommercialResult)

    async def get_cheermotes(self,
                             broadcaster_id: str) -> GetCheermotesResponse:
        """Retrieves the list of available Cheermotes, animated emotes to which viewers can assign Bits,
        to cheer in chat.\n\n

        Requires App authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-cheermotes

        :param broadcaster_id: ID for the broadcaster who might own specialized Cheermotes.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        """
        return await self._build_result('GET', 'bits/cheermotes', {'broadcaster_id': broadcaster_id}, AuthType.EITHER, [], GetCheermotesResponse)

    async def get_hype_train_events(self,
                                    broadcaster_id: str,
                                    first: Optional[int] = 1,
                                    cursor: Optional[str] = None) -> AsyncGenerator[HypeTrainEvent, None]:
        """Gets the information of the most recent Hype Train of the given channel ID.
        When there is currently an active Hype Train, it returns information about that Hype Train.
        When there is currently no active Hype Train, it returns information about the most recent Hype Train.
        After 5 days, if no Hype Train has been active, the endpoint will return an empty response.\n\n

        Requires App or User authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_HYPE_TRAIN`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-hype-train-events

        :param broadcaster_id: User ID of the broadcaster.
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`1`
        :param cursor: Cursor for forward pagination |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be between 1 and 100')
        param = {'broadcaster_id': broadcaster_id,
                 'first': first,
                 'cursor': cursor}
        async for y in self._build_generator('GET', 'hypetrain/events', param, AuthType.EITHER, [AuthScope.CHANNEL_READ_HYPE_TRAIN], HypeTrainEvent):
            yield y

    async def get_drops_entitlements(self,
                                     entitlement_id: Optional[str] = None,
                                     user_id: Optional[str] = None,
                                     game_id: Optional[str] = None,
                                     after: Optional[str] = None,
                                     first: Optional[int] = 20) -> AsyncGenerator[DropsEntitlement, None]:
        """Gets a list of entitlements for a given organization that have been granted to a game, user, or both.

        OAuth Token Client ID must have ownership of Game\n\n

        Requires App or User authentication\n
        See Twitch documentation for valid parameter combinations!\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-drops-entitlements

        :param entitlement_id: Unique Identifier of the entitlement |default| :code:`None`
        :param user_id: A Twitch User ID |default| :code:`None`
        :param game_id: A Twitch Game ID |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ValueError: if first is not in range 1 to 1000
        """
        if first is not None and (first < 1 or first > 1000):
            raise ValueError('first must be between 1 and 1000')
        can_use, auth_type, token, scope = self._get_used_either_auth([])
        if auth_type == AuthType.USER:
            if user_id is not None:
                raise ValueError('cant use user_id when using User Authentication')
        param = {
            'id': entitlement_id,
            'user_id': user_id,
            'game_id': game_id,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'entitlements/drops', param, AuthType.EITHER, [], DropsEntitlement):
            yield y

    async def create_custom_reward(self,
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
                                   should_redemptions_skip_request_queue: Optional[bool] = False) -> CustomReward:
        """Creates a Custom Reward on a channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-custom-rewards

        :param broadcaster_id: ID of the broadcaster, must be same as user_id of auth token
        :param title: The title of the reward
        :param cost: The cost of the reward
        :param prompt: The prompt for the viewer when they are redeeming the reward |default| :code:`None`
        :param is_enabled: Is the reward currently enabled, if false the reward won’t show up to viewers. |default| :code:`True`
        :param background_color: Custom background color for the reward. Format: Hex with # prefix. Example: :code:`#00E5CB`. |default| :code:`None`
        :param is_user_input_required: Does the user need to enter information when redeeming the reward. |default| :code:`False`
        :param is_max_per_stream_enabled: Whether a maximum per stream is enabled. |default| :code:`False`
        :param max_per_stream: The maximum number per stream if enabled |default| :code:`None`
        :param is_max_per_user_per_stream_enabled: Whether a maximum per user per stream is enabled. |default| :code:`False`
        :param max_per_user_per_stream: The maximum number per user per stream if enabled |default| :code:`None`
        :param is_global_cooldown_enabled: Whether a cooldown is enabled. |default| :code:`False`
        :param global_cooldown_seconds: The cooldown in seconds if enabled |default| :code:`None`
        :param should_redemptions_skip_request_queue: Should redemptions be set to FULFILLED status immediately
                    when redeemed and skip the request queue instead of the normal UNFULFILLED status. |default| :code:`False`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ValueError: if is_global_cooldown_enabled is True but global_cooldown_seconds is not specified
        :raises ValueError: if is_max_per_stream_enabled is True but max_per_stream is not specified
        :raises ValueError: if is_max_per_user_per_stream_enabled is True but max_per_user_per_stream is not specified
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if Channel Points are not available for the broadcaster
        """

        if is_global_cooldown_enabled and global_cooldown_seconds is None:
            raise ValueError('please specify global_cooldown_seconds')
        if is_max_per_stream_enabled and max_per_stream is None:
            raise ValueError('please specify max_per_stream')
        if is_max_per_user_per_stream_enabled and max_per_user_per_stream is None:
            raise ValueError('please specify max_per_user_per_stream')

        param = {'broadcaster_id': broadcaster_id}
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
        error_handler = {403: TwitchAPIException('Forbidden: Channel Points are not available for the broadcaster')}
        return await self._build_result('POST', 'channel_points/custom_rewards', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS],
                                        CustomReward, body_data=body, error_handler=error_handler)

    async def delete_custom_reward(self,
                                   broadcaster_id: str,
                                   reward_id: str):
        """Deletes a Custom Reward on a channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-custom-rewards

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param reward_id: ID of the Custom Reward to delete, must match a Custom Reward on broadcaster_id’s channel.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster has no custom reward with the given id
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the custom reward specified in reward_id was not found
        """

        await self._build_result('DELETE', 'channel_points/custom_rewards', {'broadcaster_id': broadcaster_id, 'id': reward_id}, AuthType.USER,
                                 [AuthScope.CHANNEL_MANAGE_REDEMPTIONS], None)

    async def get_custom_reward(self,
                                broadcaster_id: str,
                                reward_id: Optional[Union[str, List[str]]] = None,
                                only_manageable_rewards: Optional[bool] = False) -> Sequence[CustomReward]:
        """Returns a list of Custom Reward objects for the Custom Rewards on a channel.
        Developers only have access to update and delete rewards that the same/calling client_id created.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-custom-reward

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param reward_id: When used, this parameter filters the results and only returns reward objects for the Custom Rewards with matching ID.
                Maximum: 50 |default| :code:`None`
        :param only_manageable_rewards: When set to true, only returns custom rewards that the calling client_id can manage. |default| :code:`False`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if all custom rewards specified in reward_id where not found
        :raises ValueError: if reward_id is longer than 50 entries
        """

        if reward_id is not None and isinstance(reward_id, list) and len(reward_id) > 50:
            raise ValueError('reward_id can not contain more than 50 entries')
        param = {
            'broadcaster_id': broadcaster_id,
            'id': reward_id,
            'only_manageable_rewards': only_manageable_rewards
        }
        return await self._build_result('GET', 'channel_points/custom_rewards', param, AuthType.USER, [AuthScope.CHANNEL_READ_REDEMPTIONS],
                                        List[CustomReward], split_lists=True)

    async def get_custom_reward_redemption(self,
                                           broadcaster_id: str,
                                           reward_id: str,
                                           redemption_id: Optional[List[str]] = None,
                                           status: Optional[CustomRewardRedemptionStatus] = None,
                                           sort: Optional[SortOrder] = SortOrder.OLDEST,
                                           after: Optional[str] = None,
                                           first: Optional[int] = 20) -> AsyncGenerator[CustomRewardRedemption, None]:
        """Returns Custom Reward Redemption objects for a Custom Reward on a channel that was created by the
        same client_id.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-custom-reward-redemption

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token
        :param reward_id: When ID is not provided, this parameter returns paginated Custom
                Reward Redemption objects for redemptions of the Custom Reward with ID reward_id
        :param redemption_id: When used, this param filters the results and only returns Custom Reward Redemption objects for the
                redemptions with matching ID. Maximum: 50 ids |default| :code:`None`
        :param status: When id is not provided, this param is required and filters the paginated Custom Reward Redemption objects
                for redemptions with the matching status. |default| :code:`None`
        :param sort: Sort order of redemptions returned when getting the paginated Custom Reward Redemption objects for a reward.
                |default| :code:`SortOrder.OLDEST`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 50 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if app authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user or app authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchResourceNotFound: if all redemptions specified in redemption_id where not found
        :raises ValueError: if id has more than 50 entries
        :raises ValueError: if first is not in range 1 to 50
        :raises ValueError: if status and id are both :code:`None`
        """

        if first is not None and (first < 1 or first > 50):
            raise ValueError('first must be in range 1 to 50')
        if redemption_id is not None and len(redemption_id) > 50:
            raise ValueError('id can not have more than 50 entries')
        if status is None and redemption_id is None:
            raise ValueError('you have to set at least one of status or id')

        param = {
            'broadcaster_id': broadcaster_id,
            'reward_id': reward_id,
            'id': redemption_id,
            'status': status,
            'sort': sort,
            'after': after,
            'first': first
        }
        error_handler = {
            403: TwitchAPIException('The ID in the Client-Id header must match the client ID used to create the custom reward or '
                                    'the broadcaster is not a partner or affiliate')
        }
        async for y in self._build_generator('GET', 'channel_points/custom_rewards/redemptions', param, AuthType.USER,
                                             [AuthScope.CHANNEL_READ_REDEMPTIONS], CustomRewardRedemption, split_lists=True,
                                             error_handler=error_handler):
            yield y

    async def update_custom_reward(self,
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
                                   is_paused: Optional[bool] = False,
                                   should_redemptions_skip_request_queue: Optional[bool] = False) -> CustomReward:
        """Updates a Custom Reward created on a channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-custom-reward

        :param broadcaster_id: ID of the broadcaster, must be same as user_id of auth token
        :param reward_id: ID of the reward that you want to update
        :param title: The title of the reward |default| :code:`None`
        :param prompt: The prompt for the viewer when they are redeeming the reward |default| :code:`None`
        :param cost: The cost of the reward |default| :code:`None`
        :param is_enabled: Is the reward currently enabled, if false the reward won’t show up to viewers. |default| :code:`True`
        :param background_color: Custom background color for the reward. |default| :code:`None` Format: Hex with # prefix. Example: :code:`#00E5CB`.
        :param is_user_input_required: Does the user need to enter information when redeeming the reward. |default| :code:`False`
        :param is_max_per_stream_enabled: Whether a maximum per stream is enabled. |default| :code:`False`
        :param max_per_stream: The maximum number per stream if enabled |default| :code:`None`
        :param is_max_per_user_per_stream_enabled: Whether a maximum per user per stream is enabled. |default| :code:`False`
        :param max_per_user_per_stream: The maximum number per user per stream if enabled |default| :code:`None`
        :param is_global_cooldown_enabled: Whether a cooldown is enabled. |default| :code:`False`
        :param global_cooldown_seconds: The cooldown in seconds if enabled |default| :code:`None`
        :param is_paused: Whether to pause the reward, if true viewers cannot redeem the reward. |default| :code:`False`
        :param should_redemptions_skip_request_queue: Should redemptions be set to FULFILLED status immediately
                    when redeemed and skip the request queue instead of the normal UNFULFILLED status. |default| :code:`False`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ValueError: if is_global_cooldown_enabled is True but global_cooldown_seconds is not specified
        :raises ValueError: if is_max_per_stream_enabled is True but max_per_stream is not specified
        :raises ValueError: if is_max_per_user_per_stream_enabled is True but max_per_user_per_stream is not specified
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the custom reward specified in reward_id was not found
        :raises ValueError: if the given reward_id does not match a custom reward by the given broadcaster
        """

        if is_global_cooldown_enabled and global_cooldown_seconds is None:
            raise ValueError('please specify global_cooldown_seconds')
        elif not is_global_cooldown_enabled and global_cooldown_seconds is None:
            is_global_cooldown_enabled = None
        if is_max_per_stream_enabled and max_per_stream is None:
            raise ValueError('please specify max_per_stream')
        elif not is_max_per_stream_enabled and max_per_stream is None:
            is_max_per_stream_enabled = None
        if is_max_per_user_per_stream_enabled and max_per_user_per_stream is None:
            raise ValueError('please specify max_per_user_per_stream')
        elif not is_max_per_user_per_stream_enabled and max_per_user_per_stream is None:
            is_max_per_user_per_stream_enabled = None

        param = {
            'broadcaster_id': broadcaster_id,
            'id': reward_id
        }
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
            'is_paused': is_paused,
            'should_redemptions_skip_request_queue': should_redemptions_skip_request_queue
        }.items() if y is not None}
        error_handler = {
            403: TwitchAPIException('This custom reward was created by a different broadcaster or channel points are'
                                    'not available for the broadcaster')
        }

        return await self._build_result('PATCH', 'channel_points/custom_rewards', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_REDEMPTIONS],
                                        CustomReward, body_data=body, error_handler=error_handler)

    async def update_redemption_status(self,
                                       broadcaster_id: str,
                                       reward_id: str,
                                       redemption_ids: Union[List[str], str],
                                       status: CustomRewardRedemptionStatus) -> CustomRewardRedemption:
        """Updates the status of Custom Reward Redemption objects on a channel that are in the :code:`UNFULFILLED` status.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-redemption-status

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token.
        :param reward_id: ID of the Custom Reward the redemptions to be updated are for.
        :param redemption_ids: IDs of the Custom Reward Redemption to update, must match a
                    Custom Reward Redemption on broadcaster_id’s channel Max: 50
        :param status: The new status to set redemptions to.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        :raises ValueError: if redemption_ids is longer than 50 entries
        :raises ~twitchAPI.type.TwitchResourceNotFound: if no custom reward redemptions with status UNFULFILLED where found for the given ids
        :raises ~twitchAPI.type.TwitchAPIException: if Channel Points are not available for the broadcaster or
                        the custom reward belongs to a different broadcaster
        """
        if isinstance(redemption_ids, list) and len(redemption_ids) > 50:
            raise ValueError("redemption_ids can't have more than 50 entries")

        param = {
            'id': redemption_ids,
            'broadcaster_id': broadcaster_id,
            'reward_id': reward_id
        }
        body = {'status': status.value}
        error_handler = {
            403: TwitchAPIException('This custom reward was created by a different broadcaster or channel points are '
                                    'not available for the broadcaster')
        }
        return await self._build_result('PATCH', 'channel_points/custom_rewards/redemptions', param, AuthType.USER,
                                        [AuthScope.CHANNEL_MANAGE_REDEMPTIONS], CustomRewardRedemption, body_data=body, split_lists=True,
                                        error_handler=error_handler)

    async def get_channel_editors(self,
                                  broadcaster_id: str) -> Sequence[ChannelEditor]:
        """Gets a list of users who have editor permissions for a specific channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_EDITORS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-editors

        :param broadcaster_id: Broadcaster’s user ID associated with the channel
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'channel/editors', {'broadcaster_id': broadcaster_id}, AuthType.USER, [AuthScope.CHANNEL_READ_EDITORS],
                                        List[ChannelEditor])

    async def delete_videos(self,
                            video_ids: List[str]) -> Sequence[str]:
        """Deletes one or more videos. Videos are past broadcasts, Highlights, or uploads.
        Returns False if the User was not Authorized to delete at least one of the given videos.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_VIDEOS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-videos

        :param video_ids: ids of the videos, Limit: 5 ids
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if video_ids contains more than 5 entries or is a empty list
        """
        if video_ids is None or len(video_ids) == 0 or len(video_ids) > 5:
            raise ValueError('video_ids must contain between 1 and 5 entries')
        return await self._build_result('DELETE', 'videos', {'id': video_ids}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_VIDEOS], List[str],
                                        split_lists=True)

    async def get_user_block_list(self,
                                  broadcaster_id: str,
                                  first: Optional[int] = 20,
                                  after: Optional[str] = None) -> AsyncGenerator[BlockListEntry, None]:
        """Gets a specified user’s block list. The list is sorted by when the block occurred in descending order
        (i.e. most recent block first).

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_READ_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-block-list

        :param broadcaster_id: User ID for a twitch user
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        """

        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        param = {
            'broadcaster_id': broadcaster_id,
            'first': first,
            'after': after}
        async for y in self._build_generator('GET', 'users/blocks', param, AuthType.USER, [AuthScope.USER_READ_BLOCKED_USERS], BlockListEntry):
            yield y

    async def block_user(self,
                         target_user_id: str,
                         source_context: Optional[BlockSourceContext] = None,
                         reason: Optional[BlockReason] = None) -> bool:
        """Blocks the specified user on behalf of the authenticated user.

         Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_MANAGE_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#block-user

        :param target_user_id: User ID of the user to be blocked.
        :param source_context: Source context for blocking the user. |default| :code:`None`
        :param reason: Reason for blocking the user. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid
                        and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'target_user_id': target_user_id,
            'source_context': enum_value_or_none(source_context),
            'reason': enum_value_or_none(reason)}
        return await self._build_result('PUT', 'users/blocks', param, AuthType.USER, [AuthScope.USER_MANAGE_BLOCKED_USERS], None,
                                        result_type=ResultType.STATUS_CODE) == 204

    async def unblock_user(self,
                           target_user_id: str) -> bool:
        """Unblocks the specified user on behalf of the authenticated user.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_MANAGE_BLOCKED_USERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#unblock-user

        :param target_user_id: User ID of the user to be unblocked.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('DELETE', 'users/blocks', {'target_user_id': target_user_id}, AuthType.USER,
                                        [AuthScope.USER_MANAGE_BLOCKED_USERS], None, result_type=ResultType.STATUS_CODE) == 204

    async def get_followed_streams(self,
                                   user_id: str,
                                   after: Optional[str] = None,
                                   first: Optional[int] = 100) -> AsyncGenerator[Stream, None]:
        """Gets information about active streams belonging to channels that the authenticated user follows.
        Streams are returned sorted by number of current viewers, in descending order.
        Across multiple pages of results, there may be duplicate or missing streams, as viewers join and leave streams.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_READ_FOLLOWS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-followed-streams

        :param user_id: Results will only include active streams from the channels that this Twitch user follows.
                user_id must match the User ID in the bearer token.
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default| :code:`100`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first must be in range 1 to 100')
        param = {
            'user_id': user_id,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'streams/followed', param, AuthType.USER, [AuthScope.USER_READ_FOLLOWS], Stream):
            yield y

    async def get_polls(self,
                        broadcaster_id: str,
                        poll_id: Union[None, str, List[str]] = None,
                        after: Optional[str] = None,
                        first: Optional[int] = 20) -> AsyncGenerator[Poll, None]:
        """Get information about all polls or specific polls for a Twitch channel. Poll information is available for 90 days.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-polls

        :param broadcaster_id: The broadcaster running polls.
                Provided broadcaster_id must match the user_id in the user OAuth token.
        :param poll_id: ID(s) of a poll. You can specify up to 20 poll ids |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 20 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if none of the IDs in poll_id where found
        :raises ValueError: if first is not in range 1 to 20
        :raises ValueError: if poll_id has more than 20 entries
        """
        if poll_id is not None and isinstance(poll_id, List) and len(poll_id) > 20:
            raise ValueError('You may only specify up to 20 poll IDs')
        if first is not None and (first < 1 or first > 20):
            raise ValueError('first must be in range 1 to 20')
        param = {
            'broadcaster_id': broadcaster_id,
            'id': poll_id,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'polls', param, AuthType.USER, [AuthScope.CHANNEL_READ_POLLS], Poll, split_lists=True):
            yield y

    async def create_poll(self,
                          broadcaster_id: str,
                          title: str,
                          choices: List[str],
                          duration: int,
                          channel_points_voting_enabled: bool = False,
                          channel_points_per_vote: Optional[int] = None) -> Poll:
        """Create a poll for a specific Twitch channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-poll

        :param broadcaster_id: The broadcaster running the poll
        :param title: Question displayed for the poll
        :param choices: List of poll choices.
        :param duration: Total duration for the poll (in seconds). Minimum 15, Maximum 1800
        :param channel_points_voting_enabled: Indicates if Channel Points can be used for voting. |default| :code:`False`
        :param channel_points_per_vote: Number of Channel Points required to vote once with Channel Points.
            Minimum: 0. Maximum: 1000000. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if duration is not in range 15 to 1800
        :raises ValueError: if channel_points_per_vote is not in range 0 to 1000000
        """
        if duration < 15 or duration > 1800:
            raise ValueError('duration must be between 15 and 1800')
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
            'channel_points_voting_enabled': channel_points_voting_enabled,
            'channel_points_per_vote': channel_points_per_vote
        }.items() if v is not None}
        return await self._build_result('POST', 'polls', {}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_POLLS], Poll, body_data=body)

    async def end_poll(self,
                       broadcaster_id: str,
                       poll_id: str,
                       status: PollStatus) -> Poll:
        """End a poll that is currently active.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_POLLS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#end-poll

        :param broadcaster_id: id of the broadcaster running the poll
        :param poll_id: id of the poll
        :param status: The poll status to be set
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if status is not TERMINATED or ARCHIVED
        """
        if status not in (PollStatus.TERMINATED, PollStatus.ARCHIVED):
            raise ValueError('status must be either TERMINATED or ARCHIVED')
        body = {
            'broadcaster_id': broadcaster_id,
            'id': poll_id,
            'status': status.value
        }
        return await self._build_result('PATCH', 'polls', {}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_POLLS], Poll, body_data=body)

    async def get_predictions(self,
                              broadcaster_id: str,
                              prediction_ids: Optional[List[str]] = None,
                              after: Optional[str] = None,
                              first: Optional[int] = 20) -> AsyncGenerator[Prediction, None]:
        """Get information about all Channel Points Predictions or specific Channel Points Predictions for a Twitch channel.
        Results are ordered by most recent, so it can be assumed that the currently active or locked Prediction will be the first item.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-predictions

        :param broadcaster_id: The broadcaster running the prediction
        :param prediction_ids: List of prediction ids. |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 20 |default| :code:`20`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not in range 1 to 20
        :raises ValueError: if prediction_ids contains more than 100 entries
        """
        if first is not None and (first < 1 or first > 20):
            raise ValueError('first must be in range 1 to 20')
        if prediction_ids is not None and len(prediction_ids) > 100:
            raise ValueError('maximum of 100 prediction ids allowed')

        param = {
            'broadcaster_id': broadcaster_id,
            'id': prediction_ids,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'predictions', param, AuthType.USER, [AuthScope.CHANNEL_READ_PREDICTIONS], Prediction,
                                             split_lists=True):
            yield y

    async def create_prediction(self,
                                broadcaster_id: str,
                                title: str,
                                outcomes: List[str],
                                prediction_window: int) -> Prediction:
        """Create a Channel Points Prediction for a specific Twitch channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-prediction

        :param broadcaster_id: The broadcaster running the prediction
        :param title: Title of the Prediction
        :param outcomes: List of possible Outcomes, must contain between 2 and 10 entries
        :param prediction_window: Total duration for the Prediction (in seconds). Minimum 1, Maximum 1800
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if prediction_window is not in range 1 to 1800
        :raises ValueError: if outcomes does not contain exactly 2 entries
        """
        if prediction_window < 1 or prediction_window > 1800:
            raise ValueError('prediction_window must be in range 1 to 1800')
        if len(outcomes) < 2 or len(outcomes) > 10:
            raise ValueError('outcomes must have between 2 entries and 10 entries')
        body = {
            'broadcaster_id': broadcaster_id,
            'title': title,
            'outcomes': [{'title': x} for x in outcomes],
            'prediction_window': prediction_window
        }
        return await self._build_result('POST', 'predictions', {}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_PREDICTIONS], Prediction, body_data=body)

    async def end_prediction(self,
                             broadcaster_id: str,
                             prediction_id: str,
                             status: PredictionStatus,
                             winning_outcome_id: Optional[str] = None) -> Prediction:
        """Lock, resolve, or cancel a Channel Points Prediction.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#end-prediction

        :param broadcaster_id: ID of the broadcaster
        :param prediction_id: ID of the Prediction
        :param status: The Prediction status to be set.
        :param winning_outcome_id: ID of the winning outcome for the Prediction. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if winning_outcome_id is None and status is RESOLVED
        :raises ValueError: if status is not one of RESOLVED, CANCELED or LOCKED
        :raises ~twitchAPI.type.TwitchResourceNotFound: if prediction_id or winning_outcome_id where not found
        """
        if status not in (PredictionStatus.RESOLVED, PredictionStatus.CANCELED, PredictionStatus.LOCKED):
            raise ValueError('status has to be one of RESOLVED, CANCELED or LOCKED')
        if status == PredictionStatus.RESOLVED and winning_outcome_id is None:
            raise ValueError('need to specify winning_outcome_id for status RESOLVED')
        body = {
            'broadcaster_id': broadcaster_id,
            'id': prediction_id,
            'status': status.value
        }
        if winning_outcome_id is not None:
            body['winning_outcome_id'] = winning_outcome_id
        return await self._build_result('PATCH', 'predictions', {}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_PREDICTIONS], Prediction, body_data=body)

    async def start_raid(self,
                         from_broadcaster_id: str,
                         to_broadcaster_id: str) -> RaidStartResult:
        """ Raid another channel by sending the broadcaster’s viewers to the targeted channel.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_RAIDS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#start-a-raid

        :param from_broadcaster_id: The ID of the broadcaster that's sending the raiding party.
        :param to_broadcaster_id: The ID of the broadcaster to raid.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the target channel was not found
        """
        param = {
            'from_broadcaster_id': from_broadcaster_id,
            'to_broadcaster_id': to_broadcaster_id
        }
        return await self._build_result('POST', 'raids', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_RAIDS], RaidStartResult)

    async def cancel_raid(self,
                          broadcaster_id: str):
        """Cancel a pending raid.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_RAIDS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#cancel-a-raid

        :param broadcaster_id: The ID of the broadcaster that sent the raiding party.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster does not have a pending raid to cancel
        """
        await self._build_result('DELETE', 'raids', {'broadcaster_id': broadcaster_id}, AuthType.USER, [AuthScope.CHANNEL_MANAGE_RAIDS], None)

    async def manage_held_automod_message(self,
                                          user_id: str,
                                          msg_id: str,
                                          action: AutoModAction):
        """Allow or deny a message that was held for review by AutoMod.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_AUTOMOD`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#manage-held-automod-messages

        :param user_id: The moderator who is approving or rejecting the held message.
        :param msg_id: ID of the targeted message
        :param action: The action to take for the message.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the message specified in msg_id was not found
        """
        body = {
            'user_id': user_id,
            'msg_id': msg_id,
            'action': action.value
        }
        await self._build_result('POST', 'moderation/automod/message', {}, AuthType.USER, [AuthScope.MODERATOR_MANAGE_AUTOMOD], None, body_data=body)

    async def get_chat_badges(self, broadcaster_id: str) -> Sequence[ChatBadge]:
        """Gets a list of custom chat badges that can be used in chat for the specified channel.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-chat-badges

        :param broadcaster_id: The ID of the broadcaster whose chat badges you want to get.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'chat/badges', {'broadcaster_id': broadcaster_id}, AuthType.EITHER, [], List[ChatBadge])

    async def get_global_chat_badges(self) -> Sequence[ChatBadge]:
        """Gets a list of chat badges that can be used in chat for any channel.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-global-chat-badges

        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'chat/badges/global', {}, AuthType.EITHER, [], List[ChatBadge])

    async def get_channel_emotes(self, broadcaster_id: str) -> GetChannelEmotesResponse:
        """Gets all emotes that the specified Twitch channel created.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-emotes

        :param broadcaster_id: ID of the broadcaster
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'chat/emotes', {'broadcaster_id': broadcaster_id}, AuthType.EITHER, [], GetChannelEmotesResponse,
                                        get_from_data=False)

    async def get_global_emotes(self) -> GetEmotesResponse:
        """Gets all global emotes.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-global-emotes

        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'chat/emotes/global', {}, AuthType.EITHER, [], GetEmotesResponse, get_from_data=False)

    async def get_emote_sets(self, emote_set_id: List[str]) -> GetEmotesResponse:
        """Gets emotes for one or more specified emote sets.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-emote-sets

        :param emote_set_id: A list of IDs that identify the emote sets.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        if len(emote_set_id) == 0 or len(emote_set_id) > 25:
            raise ValueError('you need to specify between 1 and 25 emote_set_ids')
        return await self._build_result('GET', 'chat/emotes/set', {'emote_set_id': emote_set_id}, AuthType.EITHER, [], GetEmotesResponse,
                                        get_from_data=False, split_lists=True)

    async def create_eventsub_subscription(self,
                                           subscription_type: str,
                                           version: str,
                                           condition: dict,
                                           transport: dict):
        """Creates an EventSub subscription.

        Requires Authentication and Scopes depending on Subscription & Transport used.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-eventsub-subscription

        :param subscription_type: The type of subscription to create. For a list of subscriptions that you can create, see [!Subscription Types](https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#subscription-types).
                Set this field to the value in the Name column of the Subscription Types table.
        :param version: The version number that identifies the definition of the subscription type that you want the response to use.
        :param condition: A dict that contains the parameter values that are specific to the specified subscription type.
                For the object’s required and optional fields, see the subscription type’s documentation.
        :param transport: The transport details that you want Twitch to use when sending you notifications.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the subscription was not found
        """
        data = {
            'type': subscription_type,
            'version': version,
            'condition': condition,
            'transport': transport
        }
        await self._build_iter_result('POST',
                                      'eventsub/subscriptions', {},
                                      AuthType.USER if transport['method'] == 'websocket' else AuthType.APP, [],
                                      GetEventSubSubscriptionResult, body_data=data)

    async def delete_eventsub_subscription(self, subscription_id: str, target_token: AuthType = AuthType.APP):
        """Deletes an EventSub subscription.

        Requires App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-eventsub-subscription

        :param subscription_id: The ID of the subscription
        :param target_token: The token to be used to delete the eventsub subscription. Use :const:`~twitchAPI.type.AuthType.APP` when deleting a webhook subscription
                or :const:`~twitchAPI.type.AuthType.USER` when deleting a websocket subscription.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the subscription was not found
        :raise ValueError: when :const:`~twitchAPI.twitch.Twitch.delete_eventsub_subscription.params.target_token` is not
                either :const:`~twitchAPI.type.AuthType.APP` or :const:`~twitchAPI.type.AuthType.USER`
        """
        if target_token not in (AuthType.USER, AuthType.APP):
            raise ValueError('target_token has to either be APP or USER')
        await self._build_result('DELETE', 'eventsub/subscriptions', {'id': subscription_id}, target_token, [], None)

    async def get_eventsub_subscriptions(self,
                                         status: Optional[str] = None,
                                         sub_type: Optional[str] = None,
                                         user_id: Optional[str] = None,
                                         subscription_id: Optional[str] = None,
                                         target_token: AuthType = AuthType.APP,
                                         after: Optional[str] = None) -> GetEventSubSubscriptionResult:
        """Gets a list of your EventSub subscriptions.
        The list is paginated and ordered by the oldest subscription first.

        Requires App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-eventsub-subscriptions

        :param status: Filter subscriptions by its status. |default| :code:`None`
        :param sub_type: Filter subscriptions by subscription type. |default| :code:`None`
        :param user_id: Filter subscriptions by user ID. |default| :code:`None`
        :param subscription_id: Returns an array with the subscription matching the ID (as long as it is owned by the client making the request),
                    or an empty array if there is no matching subscription. |default| :code:`None`
        :param target_token: The token to be used when getting eventsub subscriptions. \n
                    Use :const:`~twitchAPI.type.AuthType.APP` when getting webhook subscriptions or :const:`~twitchAPI.type.AuthType.USER` when getting websocket subscriptions.
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raise ValueError: when :const:`~twitchAPI.twitch.Twitch.get_eventsub_subscriptions.params.target_token` is not
                either :const:`~twitchAPI.type.AuthType.APP` or :const:`~twitchAPI.type.AuthType.USER`
        """
        if target_token not in (AuthType.USER, AuthType.APP):
            raise ValueError('target_token has to either be APP or USER')
        param = {
            'status': status,
            'type': sub_type,
            'user_id': user_id,
            'subscription_id': subscription_id,
            'after': after
        }
        return await self._build_iter_result('GET', 'eventsub/subscriptions', param, target_token, [], GetEventSubSubscriptionResult)

    async def get_channel_stream_schedule(self,
                                          broadcaster_id: str,
                                          stream_segment_ids: Optional[List[str]] = None,
                                          start_time: Optional[datetime] = None,
                                          utc_offset: Optional[str] = None,
                                          first: Optional[int] = 20,
                                          after: Optional[str] = None) -> ChannelStreamSchedule:
        """Gets all scheduled broadcasts or specific scheduled broadcasts from a channel’s stream schedule.

        Requires App or User Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-stream-schedule

        :param broadcaster_id: user id of the broadcaster
        :param stream_segment_ids: optional list of stream segment ids. Maximum 100 entries. |default| :code:`None`
        :param start_time: optional timestamp to start returning stream segments from. |default| :code:`None`
        :param utc_offset: A timezone offset to be used. |default| :code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 25 |default| :code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster has not created a streaming schedule
        :raises ValueError: if stream_segment_ids has more than 100 entries
        :raises ValueError: if first is not in range 1 to 25
        """
        if stream_segment_ids is not None and len(stream_segment_ids) > 100:
            raise ValueError('stream_segment_ids can only have 100 entries')
        if first is not None and (first > 25 or first < 1):
            raise ValueError('first has to be in range 1 to 25')
        param = {
            'broadcaster_id': broadcaster_id,
            'id': stream_segment_ids,
            'start_time': datetime_to_str(start_time),
            'utc_offset': utc_offset,
            'first': first,
            'after': after
        }
        return await self._build_iter_result('GET', 'schedule', param, AuthType.EITHER, [], ChannelStreamSchedule, split_lists=True,
                                             in_data=True, iter_field='segments')

    async def get_channel_icalendar(self, broadcaster_id: str) -> str:
        """Gets all scheduled broadcasts from a channel’s stream schedule as an iCalendar.

        Does not require Authorization\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-channel-icalendar

        :param broadcaster_id: id of the broadcaster
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'schedule/icalendar', {'broadcaster_id': broadcaster_id}, AuthType.NONE, [], str,
                                        result_type=ResultType.TEXT)

    async def update_channel_stream_schedule(self,
                                             broadcaster_id: str,
                                             is_vacation_enabled: Optional[bool] = None,
                                             vacation_start_time: Optional[datetime] = None,
                                             vacation_end_time: Optional[datetime] = None,
                                             timezone: Optional[str] = None):
        """Update the settings for a channel’s stream schedule. This can be used for setting vacation details.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-channel-stream-schedule

        :param broadcaster_id: id of the broadcaster
        :param is_vacation_enabled: indicates if Vacation Mode is enabled. |default| :code:`None`
        :param vacation_start_time: Start time for vacation |default| :code:`None`
        :param vacation_end_time: End time for vacation specified |default| :code:`None`
        :param timezone: The timezone for when the vacation is being scheduled using the IANA time zone database format.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcasters schedule was not found
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'is_vacation_enabled': is_vacation_enabled,
            'vacation_start_time': datetime_to_str(vacation_start_time),
            'vacation_end_time': datetime_to_str(vacation_end_time),
            'timezone': timezone
        }
        await self._build_result('PATCH', 'schedule/settings', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE], None)

    async def create_channel_stream_schedule_segment(self,
                                                     broadcaster_id: str,
                                                     start_time: datetime,
                                                     timezone: str,
                                                     is_recurring: bool,
                                                     duration: Optional[str] = None,
                                                     category_id: Optional[str] = None,
                                                     title: Optional[str] = None) -> ChannelStreamSchedule:
        """Create a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#create-channel-stream-schedule-segment

        :param broadcaster_id: id of the broadcaster
        :param start_time: Start time for the scheduled broadcast
        :param timezone: The timezone of the application creating the scheduled broadcast using the IANA time zone database format.
        :param is_recurring: Indicates if the scheduled broadcast is recurring weekly.
        :param duration: Duration of the scheduled broadcast in minutes from the start_time. |default| :code:`240`
        :param category_id: Game/Category ID for the scheduled broadcast. |default| :code:`None`
        :param title: Title for the scheduled broadcast. |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {'broadcaster_id': broadcaster_id}
        body = remove_none_values({
            'start_time': datetime_to_str(start_time),
            'timezone': timezone,
            'is_recurring': is_recurring,
            'duration': duration,
            'category_id': category_id,
            'title': title
        })
        return await self._build_iter_result('POST', 'schedule/segment', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE],
                                             ChannelStreamSchedule, body_data=body, in_data=True, iter_field='segments')

    async def update_channel_stream_schedule_segment(self,
                                                     broadcaster_id: str,
                                                     stream_segment_id: str,
                                                     start_time: Optional[datetime] = None,
                                                     duration: Optional[str] = None,
                                                     category_id: Optional[str] = None,
                                                     title: Optional[str] = None,
                                                     is_canceled: Optional[bool] = None,
                                                     timezone: Optional[str] = None) -> ChannelStreamSchedule:
        """Update a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-channel-stream-schedule-segment

        :param broadcaster_id: id of the broadcaster
        :param stream_segment_id: The ID of the streaming segment to update.
        :param start_time: Start time for the scheduled broadcast |default| :code:`None`
        :param duration: Duration of the scheduled broadcast in minutes from the start_time. |default| :code:`240`
        :param category_id: Game/Category ID for the scheduled broadcast. |default| :code:`None`
        :param title: Title for the scheduled broadcast. |default| :code:`None`
        :param is_canceled: Indicated if the scheduled broadcast is canceled. |default| :code:`None`
        :param timezone: The timezone of the application creating the scheduled broadcast using the IANA time zone database format.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the specified broadcast segment was not found
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'id': stream_segment_id
        }
        body = remove_none_values({
            'start_time': datetime_to_str(start_time),
            'duration': duration,
            'category_id': category_id,
            'title': title,
            'is_canceled': is_canceled,
            'timezone': timezone
        })
        return await self._build_iter_result('PATCH', 'schedule/segment', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE],
                                             ChannelStreamSchedule, body_data=body, in_data=True, iter_field='segments')

    async def delete_channel_stream_schedule_segment(self,
                                                     broadcaster_id: str,
                                                     stream_segment_id: str):
        """Delete a single scheduled broadcast or a recurring scheduled broadcast for a channel’s stream schedule.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_SCHEDULE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-channel-stream-schedule-segment

        :param broadcaster_id: id of the broadcaster
        :param stream_segment_id: The ID of the streaming segment to delete.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'id': stream_segment_id
        }
        await self._build_result('DELETE', 'schedule/segment', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_SCHEDULE],
                                 None)

    async def update_drops_entitlements(self,
                                        entitlement_ids: List[str],
                                        fulfillment_status: EntitlementFulfillmentStatus) -> Sequence[DropsEntitlement]:
        """Updates the fulfillment status on a set of Drops entitlements, specified by their entitlement IDs.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-drops-entitlements

        :param entitlement_ids: An array of unique identifiers of the entitlements to update.
        :param fulfillment_status: A fulfillment status.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if entitlement_ids has more than 100 entries
        """
        if len(entitlement_ids) > 100:
            raise ValueError('entitlement_ids can only have a maximum of 100 entries')
        body = remove_none_values({
            'entitlement_ids': entitlement_ids,
            'fulfillment_status': fulfillment_status.value
        })
        return await self._build_result('PATCH', 'entitlements/drops', {}, AuthType.EITHER, [], List[DropsEntitlement], body_data=body)

    async def send_whisper(self,
                           from_user_id: str,
                           to_user_id: str,
                           message: str):
        """Sends a whisper message to the specified user.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_MANAGE_WHISPERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#send-whisper

        :param from_user_id: The ID of the user sending the whisper.
        :param to_user_id: The ID of the user to receive the whisper.
        :param message: The whisper message to send.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the user specified in to_user_id was not found
        :raises ValueError: if message is empty
        """
        if len(message) == 0:
            raise ValueError('message can\'t be empty')
        param = {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id
        }
        body = {'message': message}
        await self._build_result('POST', 'whispers', param, AuthType.USER, [AuthScope.USER_MANAGE_WHISPERS], None, body_data=body)

    async def remove_channel_vip(self,
                                 broadcaster_id: str,
                                 user_id: str) -> bool:
        """Removes a VIP from the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_VIPS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#remove-channel-vip

        :param broadcaster_id: The ID of the broadcaster that’s removing VIP status from the user.
        :param user_id: The ID of the user to remove as a VIP from the broadcaster’s chat room.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the moderator_id or user_id where not found
        :returns: True if channel vip was removed, False if user was not a channel vip
        """
        param = {
            'user_id': user_id,
            'broadcaster_id': broadcaster_id
        }
        return await self._build_result('DELETE', 'channels/vips', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_VIPS], None,
                                        result_type=ResultType.STATUS_CODE) == 204

    async def add_channel_vip(self,
                              broadcaster_id: str,
                              user_id: str) -> bool:
        """Adds a VIP to the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_VIPS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#add-channel-vip

        :param broadcaster_id: The ID of the broadcaster that’s granting VIP status to the user.
        :param user_id: The ID of the user to add as a VIP in the broadcaster’s chat room.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if broadcaster does not have available VIP slots or has not completed the "Build a Community" requirements
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the broadcaster_id or user_id where not found
        :returns: True if user was added as vip, False when user was already vip or is moderator
        """
        param = {
            'user_id': user_id,
            'broadcaster_id': broadcaster_id
        }
        error_handler = {
            409: ValueError('Broadcaster does not have available VIP slots'),
            425: ValueError('The broadcaster did not complete the "Build a Community" requirements')
        }
        return await self._build_result('POST', 'channels/vips', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_VIPS], None,
                                        result_type=ResultType.STATUS_CODE, error_handler=error_handler) == 204

    async def get_vips(self,
                       broadcaster_id: str,
                       user_ids: Optional[Union[str, List[str]]] = None,
                       first: Optional[int] = None,
                       after: Optional[str] = None) -> AsyncGenerator[ChannelVIP, None]:
        """Gets a list of the channel’s VIPs.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_VIPS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-vips

        :param broadcaster_id: The ID of the broadcaster whose list of VIPs you want to get.
        :param user_ids: Filters the list for specific VIPs. Maximum 100 |default|:code:`None`
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default|:code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if you specify more than 100 user ids
        """
        if user_ids is not None and isinstance(user_ids, list) and len(user_ids) > 100:
            raise ValueError('you can only specify up to 100 user ids')
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_ids,
            'first': first,
            'after': after
        }
        async for y in self._build_generator('GET', 'channels/vips', param, AuthType.USER, [AuthScope.CHANNEL_READ_VIPS], ChannelVIP,
                                             split_lists=True):
            yield y

    async def add_channel_moderator(self,
                                    broadcaster_id: str,
                                    user_id: str):
        """Adds a moderator to the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_MODERATORS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#add-channel-moderator

        :param broadcaster_id: The ID of the broadcaster that owns the chat room.
        :param user_id: The ID of the user to add as a moderator in the broadcaster’s chat room.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: If user is a vip
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id
        }
        error_handler = {422: ValueError('User is a vip')}
        await self._build_result('POST', 'moderation/moderators', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_MODERATORS], None,
                                 error_handler=error_handler)

    async def remove_channel_moderator(self,
                                       broadcaster_id: str,
                                       user_id: str):
        """Removes a moderator from the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_MODERATORS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#remove-channel-moderator

        :param broadcaster_id: The ID of the broadcaster that owns the chat room.
        :param user_id: The ID of the user to remove as a moderator from the broadcaster’s chat room.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id
        }
        await self._build_result('DELETE', 'moderation/moderators', param, AuthType.USER, [AuthScope.CHANNEL_MANAGE_MODERATORS], None)

    async def get_user_chat_color(self,
                                  user_ids: Union[str, List[str]]) -> Sequence[UserChatColor]:
        """Gets the color used for the user’s name in chat.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-chat-color

        :param user_ids: The ID of the user whose color you want to get.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if you specify more than 100 user ids
        :return: A list of user chat Colors
        """
        if isinstance(user_ids, list) and len(user_ids) > 100:
            raise ValueError('you can only request up to 100 users at the same time')
        return await self._build_result('GET', 'chat/color', {'user_id': user_ids}, AuthType.EITHER, [], List[UserChatColor], split_lists=True)

    async def update_user_chat_color(self,
                                     user_id: str,
                                     color: str):
        """Updates the color used for the user’s name in chat.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_MANAGE_CHAT_COLOR`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-user-chat-color

        :param user_id: The ID of the user whose chat color you want to update.
        :param color: The color to use for the user’s name in chat. See twitch Docs for valid values.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'user_id': user_id,
            'color': color
        }
        await self._build_result('PUT', 'chat/color', param, AuthType.USER, [AuthScope.USER_MANAGE_CHAT_COLOR], None)

    async def delete_chat_message(self,
                                  broadcaster_id: str,
                                  moderator_id: str,
                                  message_id: Optional[str] = None):
        """Removes a single chat message or all chat messages from the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#delete-chat-messages

        :param broadcaster_id: The ID of the broadcaster that owns the chat room to remove messages from.
        :param moderator_id: The ID of a user that has permission to moderate the broadcaster’s chat room.
        :param message_id: The ID of the message to remove. If None, removes all messages from the broadcasters chat. |default|:code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.ForbiddenError: if moderator_id is not a moderator of broadcaster_id
        :raises ~twitchAPI.type.TwitchResourceNotFound: if the message_id was not found or the message was created more than 6 hours ago
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id,
            'message_id': message_id
        }
        error = {403: ForbiddenError('moderator_id is not a moderator of broadcaster_id')}
        await self._build_result('DELETE', 'moderation/chat', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES], None,
                                 error_handler=error)

    async def send_chat_announcement(self,
                                     broadcaster_id: str,
                                     moderator_id: str,
                                     message: str,
                                     color: Optional[str] = None):
        """Sends an announcement to the broadcaster’s chat room.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#send-chat-announcement

        :param broadcaster_id: The ID of the broadcaster that owns the chat room to send the announcement to.
        :param moderator_id: The ID of a user who has permission to moderate the broadcaster’s chat room.
        :param message: The announcement to make in the broadcaster’s chat room.
        :param color: The color used to highlight the announcement. See twitch Docs for valid values. |default|:code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.ForbiddenError: if moderator_id is not a moderator of broadcaster_id
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        body = remove_none_values({
            'message': message,
            'color': color
        })
        error = {403: ForbiddenError('moderator_id is not a moderator of broadcaster_id')}
        await self._build_result('POST', 'chat/announcements', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS], None,
                                 body_data=body, error_handler=error)

    async def send_a_shoutout(self,
                              from_broadcaster_id: str,
                              to_broadcaster_id: str,
                              moderator_id: str) -> None:
        """Sends a Shoutout to the specified broadcaster.\n
        Typically, you send Shoutouts when you or one of your moderators notice another broadcaster in your chat, the other broadcaster is coming up
        in conversation, or after they raid your broadcast.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#send-a-shoutout

        :param from_broadcaster_id: The ID of the broadcaster that’s sending the Shoutout.
        :param to_broadcaster_id: The ID of the broadcaster that’s receiving the Shoutout.
        :param moderator_id: The ID of the broadcaster or a user that is one of the broadcaster’s moderators.
            This ID must match the user ID in the access token.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ~twitchAPI.type.TwitchAPIException: if the user in moderator_id is not one of the broadcasters moderators or the broadcaster
            can't send to_broadcaster_id a shoutout
        """
        param = {
            'from_broadcaster_id': from_broadcaster_id,
            'to_broadcaster_id': to_broadcaster_id,
            'moderator_id': moderator_id
        }
        err = {403: TwitchAPIException(f'Forbidden: the user with ID {moderator_id} is not one of the moderators broadcasters or '
                                       f"the broadcaster can't send {to_broadcaster_id} a shoutout")}
        await self._build_result('POST', 'chat/shoutouts', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_SHOUTOUTS], None, error_handler=err)

    async def get_chatters(self,
                           broadcaster_id: str,
                           moderator_id: str,
                           first: Optional[int] = None,
                           after: Optional[str] = None) -> GetChattersResponse:
        """Gets the list of users that are connected to the broadcaster’s chat session.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_CHATTERS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-chatters

        :param broadcaster_id: The ID of the broadcaster whose list of chatters you want to get.
        :param moderator_id: The ID of the broadcaster or one of the broadcaster’s moderators.
                    This ID must match the user ID in the user access token.
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 1000 |default| :code:`100`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is not between 1 and 1000
        """
        if first is not None and (first < 1 or first > 1000):
            raise ValueError('first must be between 1 and 1000')

        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id,
            'first': first,
            'after': after
        }
        return await self._build_iter_result('GET', 'chat/chatters', param, AuthType.USER, [AuthScope.MODERATOR_READ_CHATTERS], GetChattersResponse)

    async def get_shield_mode_status(self,
                                     broadcaster_id: str,
                                     moderator_id: str) -> ShieldModeStatus:
        """Gets the broadcaster’s Shield Mode activation status.

        Requires User Authentication with either :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHIELD_MODE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-shield-mode-status

        :param broadcaster_id: The ID of the broadcaster whose Shield Mode activation status you want to get.
        :param moderator_id: The ID of the broadcaster or a user that is one of the broadcaster’s moderators.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        return await self._build_result('GET', 'moderation/shield_mode', param, AuthType.USER,
                                        [[AuthScope.MODERATOR_READ_SHIELD_MODE, AuthScope.MODERATOR_MANAGE_SHIELD_MODE]], ShieldModeStatus)

    async def update_shield_mode_status(self,
                                        broadcaster_id: str,
                                        moderator_id: str,
                                        is_active: bool) -> ShieldModeStatus:
        """Activates or deactivates the broadcaster’s Shield Mode.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHIELD_MODE`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#update-shield-mode-status

        :param broadcaster_id: The ID of the broadcaster whose Shield Mode you want to activate or deactivate.
        :param moderator_id: The ID of the broadcaster or a user that is one of the broadcaster’s moderators.
        :param is_active: A Boolean value that determines whether to activate Shield Mode.
                Set to true to activate Shield Mode; otherwise, false to deactivate Shield Mode.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        return await self._build_result('PUT', 'moderation/shield_mode', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_SHIELD_MODE],
                                        ShieldModeStatus, body_data={'is_active': is_active})

    async def get_charity_campaign(self,
                                   broadcaster_id: str) -> Optional[CharityCampaign]:
        """Gets information about the charity campaign that a broadcaster is running.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-charity-campaign

        :param broadcaster_id: The ID of the broadcaster that’s currently running a charity campaign.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET', 'charity/campaigns', {'broadcaster_id': broadcaster_id}, AuthType.USER,
                                        [AuthScope.CHANNEL_READ_CHARITY], CharityCampaign)

    async def get_charity_donations(self,
                                    broadcaster_id: str,
                                    first: Optional[int] = None,
                                    after: Optional[str] = None) -> AsyncGenerator[CharityCampaignDonation, None]:
        """Gets the list of donations that users have made to the broadcaster’s active charity campaign.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-charity-campaign-donations

        :param broadcaster_id: The ID of the broadcaster that’s currently running a charity campaign.
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default|:code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'first': first,
            'after': after
        }
        async for y in self._build_generator('GET', 'charity/donations', param, AuthType.USER, [AuthScope.CHANNEL_READ_CHARITY],
                                             CharityCampaignDonation):
            yield y

    async def get_content_classification_labels(self, locale: Optional[str] = None) -> Sequence[ContentClassificationLabel]:
        """Gets information about Twitch content classification labels.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-content-classification-labels

        :param locale: Locale for the Content Classification Labels. |default|:code:`en-US`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET',
                                        'content_classification_labels',
                                        {'locale': locale},
                                        AuthType.EITHER, [],
                                        List[ContentClassificationLabel])

    async def get_ad_schedule(self,
                              broadcaster_id: str) -> AdSchedule:
        """This endpoint returns ad schedule related information, including snooze, when the last ad was run,
        when the next ad is scheduled, and if the channel is currently in pre-roll free time. Note that a new ad cannot
        be run until 8 minutes after running a previous ad.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_ADS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-ad-schedule

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('GET',
                                        'channels/ads',
                                        {'broadcaster_id': broadcaster_id},
                                        AuthType.USER, [AuthScope.CHANNEL_READ_ADS],
                                        AdSchedule)

    async def snooze_next_ad(self,
                             broadcaster_id: str) -> AdSnoozeResponse:
        """If available, pushes back the timestamp of the upcoming automatic mid-roll ad by 5 minutes.
        This endpoint duplicates the snooze functionality in the creator dashboard’s Ads Manager.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_ADS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#snooze-next-ad

        :param broadcaster_id: Provided broadcaster_id must match the user_id in the auth token.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        return await self._build_result('POST',
                                        'channels/ads/schedule/snooze',
                                        {'broadcaster_id': broadcaster_id},
                                        AuthType.USER, [AuthScope.CHANNEL_MANAGE_ADS],
                                        AdSnoozeResponse)

    async def send_chat_message(self,
                                broadcaster_id: str,
                                sender_id: str,
                                message: str,
                                reply_parent_message_id: Optional[str] = None,
                                for_source_only: Optional[bool] = None) -> SendMessageResponse:
        """Sends a message to the broadcaster’s chat room.

        Requires User or App Authentication with :const:`~twitchAPI.type.AuthScope.USER_WRITE_CHAT` \n
        If App Authorization is used, then additionally requires :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from the
        chatting user and either :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` from the broadcaster or moderator status.\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#send-chat-message

        :param broadcaster_id: The ID of the broadcaster whose chat room the message will be sent to.
        :param sender_id: The ID of the user sending the message. This ID must match the user ID in the user access token.
        :param message: The message to send. The message is limited to a maximum of 500 characters.
            Chat messages can also include emoticons. To include emoticons, use the name of the emote.
            The names are case sensitive. Don’t include colons around the name (e.g., :bleedPurple:).
            If Twitch recognizes the name, Twitch converts the name to the emote before writing the chat message to the chat room
        :param reply_parent_message_id: The ID of the chat message being replied to.
        :param for_source_only: Determines if the chat message is sent only to the source channel (defined by broadcaster_id) during a shared chat session.
            This has no effect if the message is sent during a shared chat session. \n
            This parameter can only be set when utilizing App Authentication.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'broadcaster_id': broadcaster_id,
            'sender_id': sender_id,
            'message': message,
            'reply_parent_message_id': reply_parent_message_id,
            'for_source_only': for_source_only
        }
        return await self._build_result('POST',
                                        'chat/messages',
                                        param,
                                        AuthType.EITHER, [AuthScope.USER_WRITE_CHAT],
                                        SendMessageResponse)

    async def get_moderated_channels(self,
                                     user_id: str,
                                     after: Optional[str] = None,
                                     first: Optional[int] = None) -> AsyncGenerator[ChannelModerator, None]:
        """Gets a list of channels that the specified user has moderator privileges in.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_READ_MODERATED_CHANNELS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-moderated-channels

        :param user_id: A user’s ID. Returns the list of channels that this user has moderator privileges in.
                     This ID must match the user ID in the user OAuth token
        :param first: The maximum number of items to return per API call.
                     You can use this in combination with :const:`~twitchAPI.helper.limit()` to optimize the bandwidth and number of API calls used to
                     fetch the amount of results you desire.\n
                     Minimum 1, Maximum 100 |default|:code:`20`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if first is set and not in range 1 to 100
        """
        if first is not None and (first < 1 or first > 100):
            raise ValueError('first has to be between 1 and 100')
        param = {
            'user_id': user_id,
            'after': after,
            'first': first
        }
        async for y in self._build_generator('GET', 'moderation/channels', param,
                                             AuthType.USER, [AuthScope.USER_READ_MODERATED_CHANNELS],
                                             ChannelModerator):
            yield y

    async def get_user_emotes(self,
                              user_id: str,
                              broadcaster_id: Optional[str] = None,
                              after: Optional[str] = None) -> UserEmotesResponse:
        """Retrieves emotes available to the user across all channels.

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.USER_READ_EMOTES`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-user-emotes

        :param user_id: The ID of the user. This ID must match the user ID in the user access token.
        :param broadcaster_id: The User ID of a broadcaster you wish to get follower emotes of. Using this query parameter will guarantee inclusion
                    of the broadcaster’s follower emotes in the response body.\n
                    Note: If the user specified in user_id is subscribed to the broadcaster specified, their follower emotes will appear in the
                    response body regardless if this query parameter is used.
                    |default| :code:`None`
        :param after: Cursor for forward pagination.\n
                    Note: The library handles pagination on its own, only use this parameter if you get a pagination cursor via other means.
                    |default| :code:`None`
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        """
        param = {
            'user_id': user_id,
            'after': after,
            'broadcaster_id': broadcaster_id
        }
        return await self._build_iter_result('GET', 'chat/emotes/user', param,
                                             AuthType.USER, [AuthScope.USER_READ_EMOTES],
                                             UserEmotesResponse)

    async def warn_chat_user(self,
                             broadcaster_id: str,
                             moderator_id: str,
                             user_id: str,
                             reason: str) -> WarnResponse:
        """Warns a user in the specified broadcaster’s chat room, preventing them from chat interaction until the warning is acknowledged.
        New warnings can be issued to a user when they already have a warning in the channel (new warning will replace old warning).

        Requires User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_WARNINGS`\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#warn-chat-user

        :param broadcaster_id: The ID of the channel in which the warning will take effect.
        :param moderator_id: The ID of the twitch user who requested the warning.
        :param user_id: The ID of the twitch user to be warned.
        :param reason: A custom reason for the warning. Max 500 chars.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.MissingScopeException: if the user authentication is missing the required scope
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :raises ValueError: if :const:`~twitchAPI.twitch.Twitch.warn_chat_user.params.reason` is longer than 500 characters
        """
        if len(reason) > 500:
            raise ValueError('reason has to be les than 500 characters long')
        param = {
            'broadcaster_id': broadcaster_id,
            'moderator_id': moderator_id
        }
        data = {
            'data': [{
                'user_id': user_id,
                'reason': reason
            }]
        }
        return await self._build_result('POST', 'moderation/warnings', param, AuthType.USER, [AuthScope.MODERATOR_MANAGE_WARNINGS],
                                        WarnResponse, body_data=data)

    async def get_shared_chat_session(self, broadcaster_id: str) -> Optional[SharedChatSession]:
        """Retrieves the active shared chat session for a channel.

        Requires User or App Authentication\n
        For detailed documentation, see here: https://dev.twitch.tv/docs/api/reference#get-shared-chat-session

        :param broadcaster_id: The User ID of the channel broadcaster.
        :raises ~twitchAPI.type.TwitchAPIException: if the request was malformed
        :raises ~twitchAPI.type.UnauthorizedException: if user authentication is not set or invalid
        :raises ~twitchAPI.type.TwitchAuthorizationException: if the used authentication token became invalid and a re authentication failed
        :raises ~twitchAPI.type.TwitchBackendException: if the Twitch API itself runs into problems
        :raises ~twitchAPI.type.TwitchAPIException: if a Query Parameter is missing or invalid
        :returns: None if there is no active shared chat session
        """
        param = {
            'broadcaster_id': broadcaster_id
        }
        return await self._build_result('GET', 'shared_chat/session', param, AuthType.EITHER, [], SharedChatSession)
