#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""Type Definitions"""

from enum import Enum
from typing_extensions import TypedDict


class AnalyticsReportType(Enum):
    """Enum of all Analytics report types
    """
    V1 = 'overview_v1'
    V2 = 'overview_v2'


class AuthScope(Enum):
    """Enum of Authentication scopes
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
    USER_READ_FOLLOWS = 'user:read:follows'
    CHANNEL_READ_GOALS = 'channel:read:goals'
    CHANNEL_READ_POLLS = 'channel:read:polls'
    CHANNEL_MANAGE_POLLS = 'channel:manage:polls'
    CHANNEL_READ_PREDICTIONS = 'channel:read:predictions'
    CHANNEL_MANAGE_PREDICTIONS = 'channel:manage:predictions'
    MODERATOR_MANAGE_AUTOMOD = 'moderator:manage:automod'
    CHANNEL_MANAGE_SCHEDULE = 'channel:manage:schedule'
    CHANNEL_MANAGE_CHAT_SETTINGS = 'channel:manage:chat_settings'
    MODERATOR_MANAGE_BANNED_USERS = 'moderator:manage:banned_users'
    MODERATOR_READ_BLOCKED_TERMS = 'moderator:read:blocked_terms'
    MODERATOR_MANAGE_BLOCKED_TERMS = 'moderator:manage:blocked_terms'


class ModerationEventType(Enum):
    """Enum of moderation event types
    """
    BAN = 'moderation.user.ban'
    UNBAN = 'moderation.user.unban'
    UNKNOWN = ''


class TimePeriod(Enum):
    """Enum of valid Time periods
    """
    ALL = 'all'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class SortMethod(Enum):
    """Enum of valid sort methods
    """
    TIME = 'time'
    TRENDING = 'trending'
    VIEWS = 'views'


class HypeTrainContributionMethod(Enum):
    """Enum of valid Hype Train contribution types
    """

    BITS = 'BITS'
    SUBS = 'SUBS'
    UNKNOWN = ''


class VideoType(Enum):
    """Enum of valid video types
    """
    ALL = 'all'
    UPLOAD = 'upload'
    ARCHIVE = 'archive'
    HIGHLIGHT = 'highlight'
    UNKNOWN = ''


class AuthType(Enum):
    """Type of authentication required. Only internal use
    """
    NONE = 0
    USER = 1
    APP = 2
    EITHER = 3


class CodeStatus(Enum):
    """Enum Code Status, see https://dev.twitch.tv/docs/api/reference#get-code-status for more documentation
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
    """
    BAD_MESSAGE = 'ERR_BADMESSAGE'
    BAD_AUTH = 'ERR_BADAUTH'
    SERVER = 'ERR_SERVER'
    BAD_TOPIC = 'ERR_BADTOPIC'
    NONE = ''
    UNKNOWN = 'unknown error'


class CustomRewardRedemptionStatus(Enum):
    """
    """
    UNFULFILLED = 'UNFULFILLED'
    FULFILLED = 'FULFILLED'
    CANCELED = 'CANCELED'


class SortOrder(Enum):
    """
    """
    OLDEST = 'OLDEST'
    NEWEST = 'NEWEST'


class BlockSourceContext(Enum):
    """
    """
    CHAT = 'chat'
    WHISPER = 'whisper'


class BlockReason(Enum):
    """
    """
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    OTHER = 'other'


class EntitlementFulfillmentStatus(Enum):
    """
    """
    CLAIMED = 'CLAIMED'
    FULFILLED = 'FULFILLED'


class PollStatus(Enum):
    """
    """
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    MODERATED = 'MODERATED'
    INVALID = 'INVALID'
    TERMINATED = 'TERMINATED'
    ARCHIVED = 'ARCHIVED'


class PredictionStatus(Enum):
    """
    """
    ACTIVE = 'ACTIVE'
    RESOLVED = 'RESOLVED'
    CANCELED = 'CANCELED'
    LOCKED = 'LOCKED'


class AutoModAction(Enum):
    """
    """
    ALLOW = 'ALLOW'
    DENY = 'DENY'


class AutoModCheckEntry(TypedDict):
    msg_id: str
    """Developer-generated identifier for mapping messages to results."""
    msg_text: str
    """Message text"""
    user_id: str
    """User ID of the sender"""


# EXCEPTIONS


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


class EventSubSubscriptionTimeout(TwitchAPIException):
    """When the waiting for a confirmed EventSub subscription timed out"""
    pass


class EventSubSubscriptionConflict(TwitchAPIException):
    """When you try to subscribe to a EventSub subscription that already exists"""
    pass


class EventSubSubscriptionError(TwitchAPIException):
    """if the subscription request was invalid"""
    pass


class DeprecatedError(TwitchAPIException):
    """If something has been marked as deprecated by the Twitch API"""
    pass
