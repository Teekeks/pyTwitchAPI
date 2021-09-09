#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""Helper functions"""

import urllib.parse
import uuid
from typing import Union, List, Type, Optional
from json import JSONDecodeError
from aiohttp.web import Request
from dateutil import parser as du_parser
from enum import Enum
from .types import AuthScope
from urllib.parse import urlparse, parse_qs


TWITCH_API_BASE_URL = "https://api.twitch.tv/helix/"
TWITCH_AUTH_BASE_URL = "https://id.twitch.tv/"
TWITCH_PUB_SUB_URL = "wss://pubsub-edge.twitch.tv"


def extract_uuid_str_from_url(url: str) -> Union[str, None]:
    """Extracts a UUID string from a URL

    :param str url: The URL to parse
    :return: UUID string extracted from given URL or None if no UUID found
    :rtype: Union[str, None]
    """
    uuids = parse_qs(urlparse(url).query).get('uuid', [])
    return uuids[0] if len(uuids) > 0 else None


def build_url(url: str, params: dict, remove_none=False, split_lists=False, enum_value=True) -> str:
    """Build a valid url string

    :param url: base URL
    :param params: dictionary of URL parameter
    :param bool remove_none: if set all params that have a None value get removed |default| :code:`False`
    :param bool split_lists: if set all params that are a list will be split over multiple url
            parameter with the same name |default| :code:`False`
    :param bool enum_value: if true, automatically get value string from Enum values |default| :code:`True`
    :return: URL
    :rtype: str
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


def get_uuid():
    """Returns a random UUID

    :rtype: :class:`~uuid.UUID`"""
    return uuid.uuid4()


async def get_json(request: 'Request') -> Union[list, dict, None]:
    """Tries to retrieve the json object from the body

    :param request: the request
    :return: the object in the body or None
    """
    if not request.can_read_body:
        return None
    try:
        data = await request.json()
        return data
    except JSONDecodeError:
        return None


def make_fields_datetime(data: Union[dict, list], fields: List[str]):
    """Itterates over dict or list recursivly to replace string fields with datetime

    :param union[dict, list] data: dict or list
    :param list[str] fields: list of keys to be replaced
    :rtype: union[dict, list]
    """

    def make_str_field_datetime(data, fields: list):
        if isinstance(data, str) and data in fields:
            if data == '':
                return None
            return du_parser.isoparse(data)
        return data

    def make_dict_field_datetime(data: dict, fields: list) -> dict:
        fd = data
        for key, value in data.items():
            if isinstance(value, str):
                fd[key] = make_str_field_datetime(value, fields)
            elif isinstance(value, dict):
                fd[key] = make_dict_field_datetime(value, fields)
            elif isinstance(value, list):
                fd[key] = make_fields_datetime(value, fields)
        return fd

    if isinstance(data, list):
        return [make_fields_datetime(d, fields) for d in data]
    elif isinstance(data, dict):
        return make_dict_field_datetime(data, fields)
    else:
        return make_str_field_datetime(data, fields)


def build_scope(scopes: List[AuthScope]) -> str:
    """Builds a valid scope string from list

    :param list[~twitchAPI.types.AuthScope] scopes: list of :class:`~twitchAPI.types.AuthScope`
    :rtype: str
    :returns: the valid auth scope string
    """
    return ' '.join([s.value for s in scopes])


def fields_to_enum(data: Union[dict, list],
                   fields: List[str],
                   _enum: Type[Enum],
                   default: Optional[Enum]) -> Union[dict, list]:
    """Itterates a dict or list and tries to replace every dict entry with key in fields with the correct Enum value

    :param Union[dict, list] data: dict or list
    :param list[str] fields: list of keys to be replaced
    :param _enum: Type of Enum to be replaced
    :param default: The default value if _enum does not contain the field value
    :rtype: dict or list
    """
    _enum_vals = [e.value for e in _enum.__members__.values()]

    def make_dict_field_enum(data: dict,
                             fields: List[str],
                             _enum: Type[Enum],
                             default: Optional[Enum]) -> Union[dict, Enum, None]:
        fd = data
        if isinstance(data, str):
            if data not in _enum_vals:
                return default
            else:
                return _enum(data)
        for key, value in data.items():
            # TODO fix for non string values
            if isinstance(value, str):
                if key in fields:
                    if value not in _enum_vals:
                        fd[key] = default
                    else:
                        fd[key] = _enum(value)
            elif isinstance(value, dict):
                fd[key] = make_dict_field_enum(value, fields, _enum, default)
            elif isinstance(value, list):
                fd[key] = fields_to_enum(value, fields, _enum, default)
        return fd
    if isinstance(data, list):
        return [make_dict_field_enum(d, fields, _enum, default) for d in data]
    else:
        return make_dict_field_enum(data, fields, _enum, default)


def make_enum(data: str, _enum: Type[Enum], default: Enum) -> Enum:
    _enum_vals = [e.value for e in _enum.__members__.values()]
    if data in _enum_vals:
        return _enum(data)
    else:
        return default


def enum_value_or_none(enum):
    return enum.value if enum is not None else None


def datetime_to_str(dt):
    return dt.astimezone().isoformat() if dt is not None else None


def remove_none_values(d: dict) -> dict:
    """Removes items where the value is None from the dict.
    This returns a new dict and does not manipulate the one given."""
    return {k: v for k, v in d.items() if v is not None}
