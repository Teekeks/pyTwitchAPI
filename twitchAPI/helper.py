#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Helper functions
----------------"""
import asyncio
import datetime
import logging
import time
import urllib.parse
import uuid
from logging import Logger
from typing import AsyncGenerator, TypeVar
from enum import Enum

from .type import AuthScope

from typing import Union, List, Type, Optional

__all__ = ['first', 'limit', 'TWITCH_API_BASE_URL', 'TWITCH_AUTH_BASE_URL', 'TWITCH_PUB_SUB_URL', 'TWITCH_CHAT_URL', 'TWITCH_EVENT_SUB_WEBSOCKET_URL',
           'build_url', 'get_uuid', 'build_scope', 'fields_to_enum', 'make_enum',
           'enum_value_or_none', 'datetime_to_str', 'remove_none_values', 'ResultType', 'RateLimitBucket', 'RATE_LIMIT_SIZES', 'done_task_callback']

T = TypeVar('T')

TWITCH_API_BASE_URL: str = "https://api.twitch.tv/helix/"
"""The base url to the Twitch API endpoints"""
TWITCH_AUTH_BASE_URL: str = "https://id.twitch.tv/oauth2/"
"""The base url to the twitch authentication endpoints"""
TWITCH_PUB_SUB_URL: str = "wss://pubsub-edge.twitch.tv"
"""The url to the Twitch PubSub websocket"""
TWITCH_CHAT_URL: str = "wss://irc-ws.chat.twitch.tv:443"
"""The url to the Twitch Chat websocket"""
TWITCH_EVENT_SUB_WEBSOCKET_URL: str = 'wss://eventsub.wss.twitch.tv/ws'
"""The url to the Twitch EventSub websocket"""


class ResultType(Enum):
    RETURN_TYPE = 0
    STATUS_CODE = 1
    TEXT = 2


def build_url(url: str, params: dict, remove_none: bool = False, split_lists: bool = False, enum_value: bool = True) -> str:
    """Build a valid url string

    :param url: base URL
    :param params: dictionary of URL parameter
    :param remove_none: if set all params that have a None value get removed |default| :code:`False`
    :param split_lists: if set all params that are a list will be split over multiple url parameter with the same name |default| :code:`False`
    :param enum_value: if true, automatically get value string from Enum values |default| :code:`True`
    :return: URL
    """

    def get_val(val):
        if not enum_value:
            return str(val)
        if isinstance(val, Enum):
            return str(val.value)
        return str(val)

    def add_param(res, k, v):
        if len(res) > 0:
            res += "&"
        res += str(k)
        if v is not None:
            res += "=" + urllib.parse.quote(get_val(v))
        return res

    result = ""
    for key, value in params.items():
        if value is None and remove_none:
            continue
        if split_lists and isinstance(value, list):
            for va in value:
                result = add_param(result, key, va)
        else:
            result = add_param(result, key, value)
    return url + (("?" + result) if len(result) > 0 else "")


def get_uuid() -> uuid.UUID:
    """Returns a random UUID"""
    return uuid.uuid4()


def build_scope(scopes: List[AuthScope]) -> str:
    """Builds a valid scope string from list

    :param scopes: list of :class:`~twitchAPI.type.AuthScope`
    :returns: the valid auth scope string
    """
    return ' '.join([s.value for s in scopes])


def fields_to_enum(data: Union[dict, list],
                   fields: List[str],
                   _enum: Type[Enum],
                   default: Optional[Enum]) -> Union[dict, list]:
    """Iterates a dict or list and tries to replace every dict entry with key in fields with the correct Enum value

    :param data: dict or list
    :param fields: list of keys to be replaced
    :param _enum: Type of Enum to be replaced
    :param default: The default value if _enum does not contain the field value
    """
    _enum_vals = [e.value for e in _enum.__members__.values()]

    def make_dict_field_enum(_data: dict,
                             _fields: List[str],
                             _enum: Type[Enum],
                             _default: Optional[Enum]) -> Union[dict, Enum, None]:
        fd = _data
        if isinstance(_data, str):
            if _data not in _enum_vals:
                return _default
            else:
                return _enum(_data)
        for key, value in _data.items():
            if isinstance(value, str):
                if key in fields:
                    if value not in _enum_vals:
                        fd[key] = _default
                    else:
                        fd[key] = _enum(value)
            elif isinstance(value, dict):
                fd[key] = make_dict_field_enum(value, _fields, _enum, _default)
            elif isinstance(value, list):
                fd[key] = fields_to_enum(value, _fields, _enum, _default)
        return fd

    if isinstance(data, list):
        return [make_dict_field_enum(d, fields, _enum, default) for d in data]
    else:
        return make_dict_field_enum(data, fields, _enum, default)


def make_enum(data: Union[str, int], _enum: Type[Enum], default: Enum) -> Enum:
    """Takes in a value and maps it to the given Enum. If the value is not valid it will take the default.

    :param data: the value to map from
    :param _enum: the Enum type to map to
    :param default: the default value"""
    _enum_vals = [e.value for e in _enum.__members__.values()]
    if data in _enum_vals:
        return _enum(data)
    else:
        return default


def enum_value_or_none(enum: Optional[Enum]) -> Union[None, str, int]:
    """Returns the value of the given Enum member or None

    :param enum: the Enum member"""
    return enum.value if enum is not None else None


def datetime_to_str(dt: Optional[datetime.datetime]) -> Optional[str]:
    """ISO-8601 formats the given datetime, returns None if datetime is None

    :param dt: the datetime to format"""
    return dt.astimezone().isoformat() if dt is not None else None


def remove_none_values(d: dict) -> dict:
    """Removes items where the value is None from the dict.
    This returns a new dict and does not manipulate the one given.

    :param d: the dict from which the None values should be removed"""
    return {k: v for k, v in d.items() if v is not None}


async def first(gen: AsyncGenerator[T, None]) -> Optional[T]:
    """Returns the first value of the given AsyncGenerator

    Example:

    .. code-block:: python

        user = await first(twitch.get_users())

    :param gen: The generator from which you want the first value"""
    try:
        return await gen.__anext__()
    except StopAsyncIteration:
        return None


async def limit(gen: AsyncGenerator[T, None], num: int) -> AsyncGenerator[T, None]:
    """Limits the number of entries from the given AsyncGenerator to up to num.

    This example will give you the currently 5 most watched streams:

    .. code-block:: python

        async for stream in limit(twitch.get_streams(), 5):
            print(stream.title)

    :param gen: The generator from which you want the first n values
    :param num: the number of entries you want
    :raises ValueError: if num is less than 1
    """
    if num < 1:
        raise ValueError('num has to be a int > 1')
    c = 0
    async for y in gen:
        c += 1
        if c > num:
            break
        yield y


class RateLimitBucket:
    """Handler used for chat rate limiting"""

    def __init__(self,
                 bucket_length: int,
                 bucket_size: int,
                 scope: str,
                 logger: Optional[logging.Logger] = None):
        """

        :param bucket_length: time in seconds the bucket is valid for
        :param bucket_size: the number of entries that can be put into the bucket
        :param scope: the scope of this bucket (used for logging)
        :param logger: the logger to be used. If None the default logger is used
        """
        self.scope = scope
        self.bucket_length = float(bucket_length)
        self.bucket_size = bucket_size
        self.reset = None
        self.content = 0
        self.logger = logger
        self.lock: asyncio.Lock = asyncio.Lock()

    def get_delta(self, num: int) -> Optional[float]:
        current = time.time()
        if self.reset is None:
            self.reset = current + self.bucket_length
        if current >= self.reset:
            self.reset = current + self.bucket_length
            self.content = num
        else:
            self.content += num
        if self.content >= self.bucket_size:
            return self.reset - current
        return None

    def left(self) -> int:
        """Returns the space left in the current bucket"""
        return self.bucket_size - self.content

    def _warn(self, msg):
        if self.logger is not None:
            self.logger.warning(msg)
        else:
            logging.warning(msg)

    async def put(self, num: int = 1):
        """Puts :code:`num` uses into the current bucket and waits if rate limit is hit

        :param num: the number of uses put into the current bucket"""
        async with self.lock:
            delta = self.get_delta(num)
            if delta is not None:
                self._warn(f'Bucket {self.scope} got rate limited. waiting {delta:.2f}s...')
                await asyncio.sleep(delta + 0.05)


RATE_LIMIT_SIZES = {
    'user': 20,
    'mod': 100
}


def done_task_callback(logger: Logger, task: asyncio.Task):
    """helper function used as a asyncio task done callback"""
    e = task.exception()
    if e is not None:
        logger.exception("Error while running callback", exc_info=e)
