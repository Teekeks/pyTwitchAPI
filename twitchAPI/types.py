#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from enum import Enum


class AnalyticsReportType(Enum):
    V1 = 'overview_v1'
    V2 = 'overview_v2'


class AuthScope(Enum):
    ANALYTICS_READ_EXTENSION = 'analytics:read:extensions'
    ANALYTICS_READ_GAMES = 'analytics:read:games'
    BITS_READ = 'bits:read'
    CHANNEL_READ_SUBSCRIPTIONS = 'channel:read:subscriptions'
    CLIPS_EDIT = 'clips:edit'
    USER_EDIT = 'user:edit'
    USER_EDIT_BROADCAST = 'user:edit:broadcast'
    USER_READ_BROADCAST = 'user:read:broadcast'
    USER_READ_EMAIL = 'user:read:email'


class TimePeriod(Enum):
    ALL = 'all'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class AuthType(Enum):
    NONE = 0
    USER = 1
    APP = 2


class UnauthorizedException(Exception):
    pass


class MissingScopeException(Exception):
    pass
