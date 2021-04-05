#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""Type Definitions"""

from enum import Enum


class AnalyticsReportType(Enum):
    """Enum of all Analytics report types

    :var V1:
    :var V2:
    """
    V1 = 'overview_v1'
    V2 = 'overview_v2'


class AuthScope(Enum):
    """Enum of Authentication scopes

    :var ANALYTICS_READ_EXTENSION:
    :var ANALYTICS_READ_GAMES:
    :var BITS_READ:
    :var CHANNEL_READ_SUBSCRIPTIONS:
    :var CHANNEL_READ_STREAM_KEY:
    :var CHANNEL_EDIT_COMMERCIAL:
    :var CHANNEL_READ_HYPE_TRAIN:
    :var CHANNEL_MANAGE_BROADCAST:
    :var CHANNEL_READ_REDEMPTIONS:
    :var CHANNEL_MANAGE_REDEMPTIONS:
    :var CLIPS_EDIT:
    :var USER_EDIT:
    :var USER_EDIT_BROADCAST:
    :var USER_READ_BROADCAST:
    :var USER_READ_EMAIL:
    :var USER_EDIT_FOLLOWS:
    :var CHANNEL_MODERATE:
    :var CHAT_EDIT:
    :var CHAT_READ:
    :var WHISPERS_READ:
    :var WHISPERS_EDIT:
    :var MODERATION_READ:
    :var CHANNEL_SUBSCRIPTIONS:
    :var CHANNEL_READ_EDITORS:
    :var CHANNEL_MANAGE_VIDEOS:
    :var USER_READ_BLOCKED_USERS:
    :var USER_MANAGE_BLOCKED_USERS:
    """
    ANALYTICS_READ_EXTENSION = 'analytics:read:extensions'
    ANALYTICS_READ_GAMES = 'analytics:read:games'
    BITS_READ = 'bits:read'
    CHANNEL_READ_SUBSCRIPTIONS = 'channel:read:subscriptions'
    CHANNEL_READ_STREAM_KEY = 'channel:read:stream_key'
    CHANNEL_EDIT_COMMERCIAL = 'channel:edit:commercial'
    CHANNEL_READ_HYPE_TRAIN = 'channel:read:hype_train'
    CHANNEL_MANAGE_BROADCAST = 'channel:manage:broadcast'
    CHANNEL_READ_REDEMPTIONS = 'channel:read:redemptions'
    CHANNEL_MANAGE_REDEMPTIONS = 'channel:manage:redemptions'
    CLIPS_EDIT = 'clips:edit'
    USER_EDIT = 'user:edit'
    USER_EDIT_BROADCAST = 'user:edit:broadcast'
    USER_READ_BROADCAST = 'user:read:broadcast'
    USER_READ_EMAIL = 'user:read:email'
    USER_EDIT_FOLLOWS = 'user:edit:follows'
    CHANNEL_MODERATE = 'channel:moderate'
    CHAT_EDIT = 'chat:edit'
    CHAT_READ = 'chat:read'
    WHISPERS_READ = 'whispers:read'
    WHISPERS_EDIT = 'whispers:edit'
    MODERATION_READ = 'moderation:read'
    CHANNEL_SUBSCRIPTIONS = 'channel_subscriptions'
    CHANNEL_READ_EDITORS = 'channel:read:editors'
    CHANNEL_MANAGE_VIDEOS = 'channel:manage:videos'
    USER_READ_BLOCKED_USERS = 'user:read:blocked_users'
    USER_MANAGE_BLOCKED_USERS = 'user:manage:blocked_users'
    USER_READ_SUBSCRIPTIONS = 'user:read:subscriptions'


class ModerationEventType(Enum):
    """Enum of moderation event types

    :var BAN:
    :var UNBAN:
    :var UNKNOWN:
    """
    BAN = 'moderation.user.ban'
    UNBAN = 'moderation.user.unban'
    UNKNOWN = ''


class TimePeriod(Enum):
    """Enum of valid Time periods

    :var ALL:
    :var DAY:
    :var WEEK:
    :var MONTH:
    :var YEAR:
    """
    ALL = 'all'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class SortMethod(Enum):
    """Enum of valid sort methods

    :var TIME:
    :var TRENDING:
    :var VIEWS:
    """
    TIME = 'time'
    TRENDING = 'trending'
    VIEWS = 'views'


class HypeTrainContributionMethod(Enum):
    """Enum of valid Hype Train contribution types

    :var BITS:
    :var SUBS:
    :var UNKNOWN:
    """

    BITS = 'BITS'
    SUBS = 'SUBS'
    UNKNOWN = ''


class VideoType(Enum):
    """Enum of valid video types

    :var ALL:
    :var UPLOAD:
    :var ARCHIVE:
    :var HIGHLIGHT:
    :var UNKNOWN:
    """
    ALL = 'all'
    UPLOAD = 'upload'
    ARCHIVE = 'archive'
    HIGHLIGHT = 'highlight'
    UNKNOWN = ''


class AuthType(Enum):
    """Type of authentication required. Only internal use

    :var NONE: No auth required
    :var USER: User auth required
    :var APP: app auth required
    """
    NONE = 0
    USER = 1
    APP = 2
    EITHER = 3


class CodeStatus(Enum):
    """Enum Code Status, see https://dev.twitch.tv/docs/api/reference#get-code-status for more documentation

    :var SUCCESSFULLY_REDEEMED:
    :var ALREADY_CLAIMED:
    :var EXPIRED:
    :var USER_NOT_ELIGIBLE:
    :var NOT_FOUND:
    :var INACTIVE:
    :var UNUSED:
    :var INCORRECT_FORMAT:
    :var INTERNAL_ERROR:
    :var UNKNOWN_VALUE:
    """
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


class PubSubResponseError(Enum):
    """
    :var BAD_MESSAGE: message is malformed
    :var BAD_AUTH: user auth token is invalid
    :var SERVER: server error
    :var BAD_TOPIC: topic is invalid
    :var NONE: no Error
    :var UNKNOWN: a unknown error
    """
    BAD_MESSAGE = 'ERR_BADMESSAGE'
    BAD_AUTH = 'ERR_BADAUTH'
    SERVER = 'ERR_SERVER'
    BAD_TOPIC = 'ERR_BADTOPIC'
    NONE = ''
    UNKNOWN = 'unknown error'


class CustomRewardRedemptionStatus(Enum):
    """
    :var UNFULFILLED:
    :var FULFILLED:
    :var CANCELED:
    """
    UNFULFILLED = 'UNFULFILLED'
    FULFILLED = 'FULFILLED'
    CANCELED = 'CANCELED'


class SortOrder(Enum):
    """
    :var OLDEST:
    :var NEWEST:
    """
    OLDEST = 'OLDEST'
    NEWEST = 'NEWEST'


class BlockSourceContext(Enum):
    """
    :var CHAT:
    :var WHISPER:
    """
    CHAT = 'chat'
    WHISPER = 'whisper'


class BlockReason(Enum):
    """
    :var SPAM:
    :var HARASSMENT:
    :var OTHER:
    """
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    OTHER = 'other'


class TwitchAPIException(Exception):
    """Base Twitch API Exception"""
    pass


class InvalidRefreshTokenException(TwitchAPIException):
    """used User Refresh Token is invalid"""
    pass


class InvalidTokenException(TwitchAPIException):
    """Used if a invalid token is set for the client"""
    pass


class NotFoundException(TwitchAPIException):
    """Resource was not found with the given parameter"""
    pass


class TwitchAuthorizationException(TwitchAPIException):
    """Exception in the Twitch Authorization"""
    pass


class UnauthorizedException(TwitchAuthorizationException):
    """Not authorized to use this"""
    pass


class MissingScopeException(TwitchAuthorizationException):
    """authorization is missing scope"""
    pass


class TwitchBackendException(TwitchAPIException):
    """when the Twitch API itself is down"""
    pass


class PubSubListenTimeoutException(TwitchAPIException):
    """when a a PubSub listen command times out"""
    pass


class MissingAppSecretException(TwitchAPIException):
    """When the app secret is not set but app authorization is attempted"""
    pass
