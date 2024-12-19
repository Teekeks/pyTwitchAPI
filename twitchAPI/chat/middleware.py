#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
Chat Command Middleware
-----------------------

A selection of preimplemented chat command middleware.

.. note:: See :doc:`/tutorial/chat-use-middleware` for a more detailed walkthough on how to use these.

Available Middleware
====================

.. list-table::
   :header-rows: 1

   * - Middleware
     - Description
   * - :const:`~twitchAPI.chat.middleware.ChannelRestriction`
     - Filters in which channels a command can be executed in.
   * - :const:`~twitchAPI.chat.middleware.UserRestriction`
     - Filters which users can execute a command.
   * - :const:`~twitchAPI.chat.middleware.StreamerOnly`
     - Restricts the use of commands to only the streamer in their channel.
   * - :const:`~twitchAPI.chat.middleware.ChannelCommandCooldown`
     - Restricts a command to only be executed once every :const:`cooldown_seconds` in a channel regardless of user.
   * - :const:`~twitchAPI.chat.middleware.ChannelUserCommandCooldown`
     - Restricts a command to be only executed once every :const:`cooldown_seconds` in a channel by a user.
   * - :const:`~twitchAPI.chat.middleware.GlobalCommandCooldown`
     - Restricts a command to be only executed once every :const:`cooldown_seconds` in any channel.


Class Documentation
===================

"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Callable, Awaitable, Dict

if TYPE_CHECKING:
    from twitchAPI.chat import ChatCommand


__all__ = ['BaseCommandMiddleware', 'ChannelRestriction', 'UserRestriction', 'StreamerOnly',
           'ChannelCommandCooldown', 'ChannelUserCommandCooldown', 'GlobalCommandCooldown', 'SharedChatOnlyCurrent']


class BaseCommandMiddleware(ABC):
    """The base for chat command middleware, extend from this when implementing your own"""

    execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None
    """If set, this handler will be called should :const:`~twitchAPI.chat.middleware.BaseCommandMiddleware.can_execute()` fail."""

    @abstractmethod
    async def can_execute(self, command: 'ChatCommand') -> bool:
        """
        return :code:`True` if the given command should execute, otherwise :code:`False`

        :param command: The command to check if it should be executed"""
        pass

    @abstractmethod
    async def was_executed(self, command: 'ChatCommand'):
        """Will be called when a command was executed, use to update internal state"""
        pass


class ChannelRestriction(BaseCommandMiddleware):
    """Filters in which channels a command can be executed in"""

    def __init__(self,
                 allowed_channel: Optional[List[str]] = None,
                 denied_channel: Optional[List[str]] = None,
                 execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param allowed_channel: if provided, the command can only be used in channels on this list
        :param denied_channel:  if provided, the command can't be used in channels on this list
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler
        self.allowed = allowed_channel if allowed_channel is not None else []
        self.denied = denied_channel if denied_channel is not None else []

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if len(self.allowed) > 0:
            if command.room.name not in self.allowed:
                return False
        return command.room.name not in self.denied

    async def was_executed(self, command: 'ChatCommand'):
        pass


class UserRestriction(BaseCommandMiddleware):
    """Filters which users can execute a command"""

    def __init__(self,
                 allowed_users: Optional[List[str]] = None,
                 denied_users: Optional[List[str]] = None,
                 execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param allowed_users: if provided, the command can only be used by one of the provided users
        :param denied_users: if provided, the command can not be used by any of the provided users
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler
        self.allowed = allowed_users if allowed_users is not None else []
        self.denied = denied_users if denied_users is not None else []

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if len(self.allowed) > 0:
            if command.user.name not in self.allowed:
                return False
        return command.user.name not in self.denied

    async def was_executed(self, command: 'ChatCommand'):
        pass


class StreamerOnly(BaseCommandMiddleware):
    """Restricts the use of commands to only the streamer in their channel"""

    def __init__(self, execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler

    async def can_execute(self, command: 'ChatCommand') -> bool:
        return command.room.name == command.user.name

    async def was_executed(self, command: 'ChatCommand'):
        pass


class ChannelCommandCooldown(BaseCommandMiddleware):
    """Restricts a command to only be executed once every :const:`cooldown_seconds` in a channel regardless of user."""

    # command -> channel -> datetime
    _last_executed: Dict[str, Dict[str, datetime]] = {}

    def __init__(self,
                 cooldown_seconds: int,
                 execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param cooldown_seconds: time in seconds a command should not be used again
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler
        self.cooldown = cooldown_seconds

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if self._last_executed.get(command.name) is None:
            return True
        last_executed = self._last_executed[command.name].get(command.room.name)
        if last_executed is None:
            return True
        since = (datetime.now() - last_executed).total_seconds()
        return since >= self.cooldown

    async def was_executed(self, command: 'ChatCommand'):
        if self._last_executed.get(command.name) is None:
            self._last_executed[command.name] = {}
            self._last_executed[command.name][command.room.name] = datetime.now()
            return
        self._last_executed[command.name][command.room.name] = datetime.now()


class ChannelUserCommandCooldown(BaseCommandMiddleware):
    """Restricts a command to be only executed once every :const:`cooldown_seconds` in a channel by a user."""

    # command -> channel -> user -> datetime
    _last_executed: Dict[str, Dict[str, Dict[str, datetime]]] = {}

    def __init__(self,
                 cooldown_seconds: int,
                 execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param cooldown_seconds: time in seconds a command should not be used again
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler
        self.cooldown = cooldown_seconds

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if self._last_executed.get(command.name) is None:
            return True
        if self._last_executed[command.name].get(command.room.name) is None:
            return True
        last_executed = self._last_executed[command.name][command.room.name].get(command.user.name)
        if last_executed is None:
            return True
        since = (datetime.now() - last_executed).total_seconds()
        return since >= self.cooldown

    async def was_executed(self, command: 'ChatCommand'):
        if self._last_executed.get(command.name) is None:
            self._last_executed[command.name] = {}
            self._last_executed[command.name][command.room.name] = {}
            self._last_executed[command.name][command.room.name][command.user.name] = datetime.now()
            return
        if self._last_executed[command.name].get(command.room.name) is None:
            self._last_executed[command.name][command.room.name] = {}
            self._last_executed[command.name][command.room.name][command.user.name] = datetime.now()
            return
        self._last_executed[command.name][command.room.name][command.user.name] = datetime.now()


class GlobalCommandCooldown(BaseCommandMiddleware):
    """Restricts a command to be only executed once every :const:`cooldown_seconds` in any channel"""

    # command -> datetime
    _last_executed: Dict[str, datetime] = {}

    def __init__(self,
                 cooldown_seconds: int,
                 execute_blocked_handler: Optional[Callable[['ChatCommand'], Awaitable[None]]] = None):
        """
        :param cooldown_seconds: time in seconds a command should not be used again
        :param execute_blocked_handler: optional specific handler for when the execution is blocked
        """
        self.execute_blocked_handler = execute_blocked_handler
        self.cooldown = cooldown_seconds

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if self._last_executed.get(command.name) is None:
            return True
        since = (datetime.now() - self._last_executed[command.name]).total_seconds()
        return since >= self.cooldown

    async def was_executed(self, command: 'ChatCommand'):
        self._last_executed[command.name] = datetime.now()


class SharedChatOnlyCurrent(BaseCommandMiddleware):
    """Restricts commands to only current chat room in Shared Chat streams"""

    async def can_execute(self, command: 'ChatCommand') -> bool:
        if command.source_room_id != command.room.room_id:
            return False
        return True

    async def was_executed(self, command: 'ChatCommand'):
        pass
