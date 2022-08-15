#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
from datetime import datetime
from typing import Optional, get_type_hints, Union, List, get_origin
from dateutil import parser as du_parser
from pprint import pprint


class TwitchObject:
    @staticmethod
    def _val_by_instance(instance, val):
        origin = get_origin(instance)
        if instance == datetime:
            return du_parser.isoparse(val) if len(val) > 0 else None
        elif origin == list:
            c = instance.__args__[0]
            return [TwitchObject._val_by_instance(c, x) for x in val]
        elif issubclass(instance, TwitchObject):
            return instance(**val)
        else:
            return instance(val)

    def __init__(self, **kwargs):
        for name, cls in self.__annotations__.items():
            if kwargs.get(name) is None:
                continue
            self.__setattr__(name, TwitchObject._val_by_instance(cls, kwargs.get(name)))


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


class CreatorGoal(TwitchObject):
    id: str
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    type: str
    description: str
    current_amount: int
    target_amount: int
    created_at: datetime


class BitsLeaderboardEntry(TwitchObject):
    user_id: str
    user_login: str
    user_name: str
    rank: int
    score: int


class BitsLeaderboard(TwitchObject):
    data: List[BitsLeaderboardEntry]
    date_range: DateRange
    total: int