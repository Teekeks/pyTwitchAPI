from enum import Enum
from datetime import datetime

# Global vars
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TwitchObject:
    def __init__(self,**kwargs):
        for name, cls_ in self.__annotations__.items():
            if cls_ == datetime:
                self.__setattr__(name,datetime.strptime(kwargs[name],DATETIME_FORMAT))
                continue
            self.__setattr__(name,cls_(kwargs[name]))


class Response:
    objects: list = []
    pagination: str | None
    __response_class: TwitchObject

    def __init__(self,
                 object_class,
                 objects: list[TwitchObject],
                 pagination_id):
        for item in objects:
            self.objects.append(object_class(item))
        self.pagination = pagination_id


class BroadcasterTypes(Enum):
    partner = 'partner'
    affiliate = 'affiliate'
    none = ''


class UserTypes(Enum):
    staff = 'staff'
    admin = 'admin'
    global_mod = 'global_mod'
    none = ''


class User(TwitchObject):
    id: str
    login: str
    display_name: str
    type: str
    broadcaster_type: BroadcasterTypes
    description: str
    profile_image_url: str
    offline_image_url: str
    view_count: int
    email: str
    created_at: datetime


class FollowUsers(TwitchObject):
    from_id: str
    from_login: str
    from_name: str
    to_id: str
    to_name: str
    followed_at: datetime
