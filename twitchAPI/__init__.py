from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token, validate_token, revoke_token
from twitchAPI.types import *
from twitchAPI.pubsub import PubSub
from twitchAPI.eventsub import EventSub
from twitchAPI.chat import *
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, Generator

VERSION = (3, 0, 0)


def paginator(func: Callable[..., dict], *args, **kwargs) -> Generator[dict, None, None]:
    """Generator which allows to automatically paginate forwards for functions that allow that functionality.
    Pass any arguments you would pass to the specified function to this function.

    Example usage:
    .. code-block:: python
        for page in paginator(twitch.get_users, to_id=user_id):
            print(page)

    :param Callable func: The function you want to paginate over
    :raises ValueError: if the given function does not support pagination
    """
    if 'after' not in func.__code__.co_varnames:
        raise ValueError('The passed function does not support forward pagination')
    result = func(*args, **kwargs)
    yield result
    while result.get('pagination', {}).get('cursor') is not None:
        pag = result.get('pagination', {}).get('cursor')
        result = func(*args, after=pag, **kwargs)
        yield result
