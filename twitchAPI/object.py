#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
from datetime import datetime
from typing import Optional, get_type_hints, Union
from dateutil import parser as du_parser
from pprint import pprint


class TwitchObject:
    def __init__(self, **kwargs):
        for name, cls in self.__annotations__.items():
            if kwargs.get(name) is None:
                continue
            if cls == datetime:
                self.__setattr__(name, du_parser.isoparse(kwargs.get(name)))
            elif cls == TwitchObject:
                self.__setattr__(name, cls(**kwargs.get(name)))
            else:
                self.__setattr__(name, cls(kwargs.get(name)))


class TwitchUser(TwitchObject):
    id: str
    login: str
    display_name: str
    type: str
    broadcaster_type: str
    description: str
    profile_image_url: str
    offline_image_url: str
    view_count: int
    email: str = None
    created_at: datetime


class TwitchUserFollow(TwitchObject):
    from_id: str
    from_login: str
    from_name: str
    to_id: str
    to_name: str
    followed_at: datetime


class DateRange(TwitchObject):
    ended_at: datetime
    started_at: datetime


class ExtensionAnalytic(TwitchObject):
    extension_id: str
    URL: str
    type: str
    date_range: DateRange


class GameAnalytics(TwitchObject):
    game_id: str
    URL: str
    type: str
    date_range: DateRange
