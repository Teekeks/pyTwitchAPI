#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
Base Objects used by the Library
--------------------------------
"""
from datetime import datetime
from enum import Enum
from typing import TypeVar, Union, Generic, Optional

from aiohttp import ClientSession
from dateutil import parser as du_parser

from twitchAPI.helper import build_url

T = TypeVar('T')

__all__ = ['TwitchObject', 'IterTwitchObject', 'AsyncIterTwitchObject']


class TwitchObject:
    """
    A lot of API calls return a child of this in some way (either directly or via generator).
    You can always use the :const:`~twitchAPI.object.TwitchObject.to_dict()` method to turn that object to a dictionary.

    Example:

    .. code-block:: python

        blocked_term = await twitch.add_blocked_term('broadcaster_id', 'moderator_id', 'bad_word')
        print(blocked_term.id)"""
    @staticmethod
    def _val_by_instance(instance, val):
        if val is None:
            return None
        origin = instance.__origin__ if hasattr(instance, '__origin__') else None
        if instance == datetime:
            if isinstance(val, int):
                # assume unix timestamp
                return None if val == 0 else datetime.fromtimestamp(val)
            # assume ISO8601 string
            return du_parser.isoparse(val) if len(val) > 0 else None
        elif origin is list:
            c = instance.__args__[0]
            return [TwitchObject._val_by_instance(c, x) for x in val]
        elif origin is dict:
            c1 = instance.__args__[0]
            c2 = instance.__args__[1]
            return {TwitchObject._val_by_instance(c1, x1): TwitchObject._val_by_instance(c2, x2) for x1, x2 in val.items()}
        elif origin == Union:
            # TODO: only works for optional pattern, fix to try out all possible patterns?
            c1 = instance.__args__[0]
            return TwitchObject._val_by_instance(c1, val)
        elif issubclass(instance, TwitchObject):
            return instance(**val)
        else:
            return instance(val)

    @staticmethod
    def _dict_val_by_instance(instance, val, include_none_values):
        if val is None:
            return None
        if instance is None:
            return val
        origin = instance.__origin__ if hasattr(instance, '__origin__') else None
        if instance == datetime:
            return val.isoformat() if val is not None else None
        elif origin is list:
            c = instance.__args__[0]
            return [TwitchObject._dict_val_by_instance(c, x, include_none_values) for x in val]
        elif origin is dict:
            c1 = instance.__args__[0]
            c2 = instance.__args__[1]
            return {TwitchObject._dict_val_by_instance(c1, x1, include_none_values):
                    TwitchObject._dict_val_by_instance(c2, x2, include_none_values) for x1, x2 in val.items()}
        elif origin is Union:
            # TODO: only works for optional pattern, fix to try out all possible patterns?
            c1 = instance.__args__[0]
            return TwitchObject._dict_val_by_instance(c1, val, include_none_values)
        elif issubclass(instance, TwitchObject):
            return val.to_dict(include_none_values)
        elif isinstance(val, Enum):
            return val.value
        return instance(val)

    @classmethod
    def _get_annotations(cls):
        d = {}
        for c in cls.mro():
            try:
                d.update(**c.__annotations__)
            except AttributeError:
                pass
        return d

    def to_dict(self, include_none_values: bool = False) -> dict:
        """build dict based on annotation types

        :param include_none_values: if fields that have None values should be included in the dictionary
        """
        d = {}
        annotations = self._get_annotations()
        for name, val in self.__dict__.items():
            val = None
            cls = annotations.get(name)
            try:
                val = getattr(self, name)
            except AttributeError:
                pass
            if val is None and not include_none_values:
                continue
            if name[0] == '_':
                continue
            d[name] = TwitchObject._dict_val_by_instance(cls, val, include_none_values)
        return d

    def __init__(self, **kwargs):
        merged_annotations = self._get_annotations()
        for name, cls in merged_annotations.items():
            if name not in kwargs.keys():
                continue
            self.__setattr__(name, TwitchObject._val_by_instance(cls, kwargs.get(name)))

    def __repr__(self):
        merged_annotations = self._get_annotations()
        args = ', '.join(['='.join([name, str(getattr(self, name))]) for name in merged_annotations.keys() if hasattr(self, name)])
        return f'{type(self).__name__}({args})'


class IterTwitchObject(TwitchObject):
    """Special type of :const:`~twitchAPI.object.TwitchObject`.
       These usually have some list inside that you may want to directly iterate over in your API usage but that also contain other useful data
       outside of that List.

       Example:

       .. code-block:: python

          lb = await twitch.get_bits_leaderboard()
          print(lb.total)
          for e in lb:
              print(f'#{e.rank:02d} - {e.user_name}: {e.score}')"""

    def __iter__(self):
        if not hasattr(self, 'data') or not isinstance(self.__getattribute__('data'), list):
            raise ValueError('Object is missing data attribute of type list')
        for i in self.__getattribute__('data'):
            yield i


class AsyncIterTwitchObject(TwitchObject, Generic[T]):
    """A few API calls will have useful data outside the list the pagination iterates over.
       For those cases, this object exist.

       Example:

       .. code-block:: python

           schedule = await twitch.get_channel_stream_schedule('user_id')
           print(schedule.broadcaster_name)
           async for segment in schedule:
               print(segment.title)"""

    def __init__(self, _data, **kwargs):
        super(AsyncIterTwitchObject, self).__init__(**kwargs)
        self.__idx = 0
        self._data = _data

    def __aiter__(self):
        return self

    def current_cursor(self) -> Optional[str]:
        """Provides the currently used forward pagination cursor"""
        return self._data['param'].get('after')

    async def __anext__(self) -> T:
        if not hasattr(self, self._data['iter_field']) or not isinstance(self.__getattribute__(self._data['iter_field']), list):
            raise ValueError(f'Object is missing {self._data["iter_field"]} attribute of type list')
        data = self.__getattribute__(self._data['iter_field'])
        if len(data) > self.__idx:
            self.__idx += 1
            return data[self.__idx - 1]
        # make request
        if self._data['param']['after'] is None:
            raise StopAsyncIteration()
        _url = build_url(self._data['url'], self._data['param'], remove_none=True, split_lists=self._data['split'])
        async with ClientSession() as session:
            response = await self._data['req'](self._data['method'], session, _url, self._data['auth_t'], self._data['auth_s'], self._data['body'])
            _data = await response.json()
        _after = _data.get('pagination', {}).get('cursor')
        self._data['param']['after'] = _after
        if self._data['in_data']:
            _data = _data['data']
        # refill data
        merged_annotations = self._get_annotations()
        for name, cls in merged_annotations.items():
            if name not in _data.keys():
                continue
            self.__setattr__(name, TwitchObject._val_by_instance(cls, _data.get(name)))
        data = self.__getattribute__(self._data['iter_field'])
        self.__idx = 1
        if len(data) == 0:
            raise StopAsyncIteration()
        return data[self.__idx - 1]
