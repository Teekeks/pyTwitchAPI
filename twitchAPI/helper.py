#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
import urllib.parse
import uuid
from typing import Union
from json import JSONDecodeError
from aiohttp.web import Request
from dateutil import parser as du_parser


TWITCH_API_BASE_URL = "https://api.twitch.tv/helix/"
TWITCH_AUTH_BASE_URL = "https://id.twitch.tv/"


def build_url(url: str, params: dict, remove_none=False, split_lists=False) -> str:
    """Build a valid url string"""
    def add_param(res, k, v):
        if len(res) > 0:
            res += "&"
        res += str(k)
        if v is not None:
            res += "=" + urllib.parse.quote(str(v))
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
    """Returns a random UUID"""
    return uuid.uuid4()


async def get_json(request: 'Request') -> Union[list, dict, None]:
    """Tries to retrieve the json object from the body"""
    if not request.can_read_body:
        return None
    try:
        data = await request.json()
        return data
    except JSONDecodeError:
        return None


def make_dict_field_datetime(data: dict, fields: list) -> dict:
    fd = data
    for key, value in data.items():
        if isinstance(value, str):
            if key in fields:
                fd[key] = du_parser.isoparse(value)
        elif isinstance(value, dict):
            fd[key] = make_dict_field_datetime(value, fields)
        elif isinstance(value, list):
            fd[key] = make_fields_datetime(value, fields)
    return fd


def make_fields_datetime(data: Union[dict, list], fields: list):
    """itterate over dict or list recursivly to replace string fields with datetime"""
    if isinstance(data, list):
        return [make_dict_field_datetime(d, fields) for d in data]
    else:
        return make_dict_field_datetime(data, fields)


def build_scope(scopes: list) -> str:
    return ' '.join([s.value for s in scopes])
