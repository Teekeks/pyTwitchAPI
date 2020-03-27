#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from .webhook import TwitchWebHook
import requests
from typing import Union, List
from .helper import build_url, TWITCH_API_BASE_URL, TWITCH_AUTH_BASE_URL, make_fields_datetime, build_scope
from datetime import datetime
from .types import AnalyticsReportType, AuthScope, AuthType, UnauthorizedException, MissingScopeException, TimePeriod
from dateutil import parser as du_parser


class Twitch:
    app_id: Union[str, None] = None
    app_secret: Union[str, None] = None
    __app_auth_token: Union[str, None] = None
    __app_auth_scope: List[AuthScope] = []
    __has_app_auth: bool = False

    __user_auth_token: Union[str, None] = None
    __user_auth_scope: List[AuthScope] = []
    __has_user_auth: bool = False

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    def __generate_header(self, auth_type: 'AuthType', required_scope: List[AuthScope]) -> dict:
        header = {"Client-ID": self.app_id}
        if auth_type == AuthType.APP:
            if not self.__has_app_auth:
                raise UnauthorizedException('Require app authentication!')
            for s in required_scope:
                if s not in self.__app_auth_scope:
                    raise MissingScopeException('Require app auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self.__app_auth_token}'
        elif auth_type == AuthType.USER:
            if not self.__has_user_auth:
                raise UnauthorizedException('require user authentication!')
            for s in self.__user_auth_scope:
                if s not in self.__user_auth_scope:
                    raise MissingScopeException('Require user auth scope ' + s.name)
            header['Authorization'] = f'Bearer {self.__user_auth_token}'
        elif self.__has_user_auth or self.__has_app_auth:
            # if no required, set one anyway to get better rate limits if possible
            header['Authorization'] = \
                f'Bearer {self.__user_auth_token if self.__has_user_auth else self.__app_auth_token}'
        return header

    def __api_post_request(self,
                           url: str,
                           auth_type: 'AuthType',
                           required_scope: List[AuthScope] = [],
                           data: Union[dict, None] = None):
        """Make POST request with Client-ID authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        if data is None:
            return requests.post(url, headers=headers)
        else:
            return requests.post(url, headers=headers, data=data)

    def __api_get_request(self, url: str,
                          auth_type: 'AuthType',
                          required_scope: List[AuthScope] = []):
        """Make GET request with Client-ID authorization"""
        headers = self.__generate_header(auth_type, required_scope)
        return requests.get(url, headers=headers)

    def __generate_app_token(self):
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'client_credentials',
            'scope': build_scope(self.__app_auth_scope)
        }
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', params)
        result = requests.post(url)
        if result.status_code != 200:
            raise Exception(f'Authentication failed with code {result.status_code} ({result.text})')
        try:
            data = result.json()
            self.__app_auth_token = data['access_token']
        except ValueError:
            raise Exception('Authentication response did not have a valid json body')
        except KeyError:
            raise Exception('Authentication response did not contain access_token')

    def authenticate_app(self, scope: List[AuthScope]):
        self.__app_auth_scope = scope
        self.__generate_app_token()
        self.__has_app_auth = True

    def set_user_authentication(self, token: str, scope: List[AuthScope]):
        self.__user_auth_token = token
        self.__user_auth_scope = scope
        self.__has_user_auth = True

    def get_webhook(self, url: str, port: int) -> 'TwitchWebHook':
        """Returns a instance of TwitchWebHook"""
        return TwitchWebHook(url,
                             self.app_id,
                             port)

    def get_webhook_subscriptions(self, first: Union[str, None] = None, after: Union[str, None] = None):
        url = build_url(TWITCH_API_BASE_URL + 'webhooks/subscriptions',
                        {'first': first, 'after': after},
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.APP)
        return response.json()

    def get_users(self, user_ids=None, logins=None):
        if user_ids is None and logins is None:
            raise Exception('please either specify user_ids or logins')
        url_params = {
            'id': user_ids,
            'login': logins
        }
        url = build_url(TWITCH_API_BASE_URL + 'users', url_params, remove_none=True, split_lists=True)
        response = self.__api_get_request(url, AuthType.NONE)
        data = response.json()
        return data

    def get_extension_analytics(self,
                                after: Union[str, None] = None,
                                extension_id: Union[str, None] = None,
                                first: int = 20,
                                ended_at: Union[datetime, None] = None,
                                started_at: Union[datetime, None] = None,
                                report_type: Union[AnalyticsReportType, None] = None):
        if ended_at is not None or started_at is not None:
            # you have to put in both:
            if ended_at is None or started_at is None:
                raise Exception('you must specify both ended_at and started_at')
            if started_at > ended_at:
                raise Exception('started_at must be before ended_at')
        if first > 100 or first < 1:
            raise Exception('first must be between 1 and 100')
        url_params = {
            'after': after,
            'ended_at': ended_at.isoformat() if ended_at is not None else None,
            'extension_id': extension_id,
            'first': first,
            'started_at': started_at.isoformat() if started_at is not None else None,
            'type': report_type.value if report_type is not None else None
        }
        url = build_url(TWITCH_API_BASE_URL + 'analytics/extensions',
                        url_params,
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, required_scope=[AuthScope.ANALYTICS_READ_EXTENSION])
        data = response.json()
        return make_fields_datetime(data, ['started_at', 'ended_at'])

    def get_game_analytics(self,
                           after: Union[str, None] = None,
                           first: int = 20,
                           game_id: Union[str, None] = None,
                           ended_at: Union[datetime, None] = None,
                           started_at: Union[datetime, None] = None,
                           report_type: Union[AnalyticsReportType, None] = None):
        if ended_at is not None or started_at is not None:
            if ended_at is None or started_at is None:
                raise Exception('you must specify both ended_at and started_at')
            if ended_at < started_at:
                raise Exception('ended_at must be after started_at')
        if first > 100 or first < 1:
            raise Exception('first must be between 1 and 100')
        url_params = {
            'after': after,
            'ended_at': ended_at.isoformat() if ended_at is not None else None,
            'first': first,
            'game_id': game_id,
            'started_at': started_at.isoformat() if started_at is not None else None,
            'type': report_type.value if report_type is not None else None
        }
        url = build_url(TWITCH_API_BASE_URL + 'analytics/games',
                        url_params,
                        remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, [AuthScope.ANALYTICS_READ_GAMES])
        data = response.json()
        return make_fields_datetime(data, ['ended_at', 'started_at'])

    def get_bits_leaderboard(self,
                             count: int = 10,
                             period: TimePeriod = TimePeriod.ALL,
                             started_at: Union[datetime, None] = None,
                             user_id: Union[str, None] = None):
        if count > 100 or count < 1:
            raise Exception('count must be between 1 and 100')
        url_params = {
            'count': count,
            'period': period.value,
            'started_at': started_at.isoformat() if started_at is not None else None,
            'user_id': user_id
        }
        url = build_url(TWITCH_API_BASE_URL + 'bits/leaderboard', url_params, remove_none=True)
        response = self.__api_get_request(url, AuthType.USER, [AuthScope.BITS_READ])
        data = response.json()
        return make_fields_datetime(data, ['ended_at', 'started_at'])

    def get_extension_transactions(self,
                                   extension_id: str,
                                   transaction_id: Union[str, None] = None,
                                   after: Union[str, None] = None,
                                   first: int = 20):
        if first > 100 or first < 1:
            raise Exception("first must be between 1 and 100")
        url_param = {
            'extension_id': extension_id,
            'id': transaction_id,
            'after': after,
            first: first
        }
        url = build_url(TWITCH_API_BASE_URL + 'extensions/transactions', url_param, remove_none=True)
        result = self.__api_get_request(url, AuthType.APP, [])
        data = result.json()
        return make_fields_datetime(data, ['timestamp'])
