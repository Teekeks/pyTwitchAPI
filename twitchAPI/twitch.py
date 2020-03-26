#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from .webhook import TwitchWebHook
import requests
from typing import Union
from .helper import build_url, TWITCH_API_BASE_URL, TWITCH_AUTH_BASE_URL, make_fields_datetime
from datetime import datetime
from .types import AnalyticsReportType, AuthScope


class Twitch:
    app_id: Union[str, None] = None
    __app_secret: Union[str, None] = None
    __auth_token: Union[str, None] = None
    __auth_scope: Union[str, None] = None

    def __init__(self, app_id: str, app_secret: str, auth_scope: Union[str, None] = None):
        self.app_id = app_id
        self.__app_secret = app_secret
        self.__auth_scope = auth_scope

    def get_auth_token(self):
        if self.__auth_token is not None:
            return self.__auth_token
        # no token yet, lets get one...
        params = {
            'client_id': self.app_id,
            'client_secret': self.__app_secret,
            'grant_type': 'client_credentials',
            'scope': self.__auth_scope
        }
        url = build_url(TWITCH_AUTH_BASE_URL + 'oauth2/token', params)
        result = requests.post(url)
        if result.status_code != 200:
            raise Exception(f'Authentication failed with code {result.status_code} ({result.text})')
        try:
            data = result.json()
            self.__auth_token = data['access_token']
        except ValueError:
            raise Exception('Authentication response did not have a valid json body')
        except KeyError:
            raise Exception('Authentication response did not contain access_token')
        return self.__auth_token

    def __api_post_request(self, url: str, data: Union[dict, None] = None):
        """Make POST request with Client-ID authorization"""
        headers = {
            "Authorization": "Bearer " + self.get_auth_token()
        }
        if data is None:
            return requests.post(url, headers=headers)
        else:
            return requests.post(url, headers=headers, data=data)

    def __api_get_request(self, url: str):
        """Make GET request with Client-ID authorization"""
        headers = {
            "Client-ID": self.app_id,
            "Authorization": "Bearer " + self.get_auth_token()
        }
        print(headers)
        return requests.get(url, headers=headers)

    def get_webhook(self, url: str, port: int, authenticate: bool = True) -> 'TwitchWebHook':
        """Returns a instance of TwitchWebHook"""
        return TwitchWebHook(url,
                             self.app_id,
                             port)

    def get_webhook_subscriptions(self, first: Union[str, None] = None, after: Union[str, None] = None):
        url = build_url(TWITCH_API_BASE_URL + 'webhooks/subscriptions',
                        {'first': first, 'after': after},
                        remove_none=True)
        response = self.__api_get_request(url)
        return response.json()

    def get_users(self, user_ids=None, logins=None):
        if user_ids is None and logins is None:
            raise Exception('please either specify user_ids or logins')
        url_params = {
            'id': user_ids,
            'login': logins
        }
        url = build_url(TWITCH_API_BASE_URL + 'users', url_params, remove_none=True, split_lists=True)
        response = self.__api_get_request(url)
        data = response.json()
        return data['data']

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
            'ended_at': ended_at,
            'extension_id': extension_id,
            'first': first,
            'started_at': started_at,
            'type': report_type.value if report_type is not None else None
        }
        url = build_url(TWITCH_API_BASE_URL + 'analytics/extensions',
                        url_params,
                        remove_none=True)
        response = self.__api_get_request(url)
        data = response.json()
        return make_fields_datetime(data, ['started_at', 'ended_at'])

