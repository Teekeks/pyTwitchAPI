#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

from enum import Enum


class AnalyticsReportType(Enum):
    V1 = 'overview_v1'
    V2 = 'overview_v2'


class AuthScope(Enum):
    """Authentication scopes"""
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
    """Type of authentication required"""
    NONE = 0
    USER = 1
    APP = 2


class CodeStatus(Enum):
    """Code Status, see https://dev.twitch.tv/docs/api/reference#get-code-status for more documentation"""
    SUCCESSFULLY_REDEEMED = 'SUCCESSFULLY_REDEEMED'
    ALREADY_CLAIMED = 'ALREADY_CLAIMED'
    EXPIRED = 'EXPIRED'
    USER_NOT_ELIGIBLE = 'USER_NOT_ELIGIBLE'
    NOT_FOUND = 'NOT_FOUND'
    INACTIVE = 'INACTIVE'
    UNUSED = 'UNUSED'
    INCORRECT_FORMAT = 'INCORRECT_FORMAT'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    UNKNOWN_VALUE = ''


class UnauthorizedException(Exception):
    pass


class MissingScopeException(Exception):
    pass
