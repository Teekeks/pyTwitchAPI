#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
Chat Command Middleware
-----------------------
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from . import ChatCommand


__all__ = ['BaseCommandMiddleware', 'ChannelRestriction', 'UserRestriction', 'StreamerOnly']


class BaseCommandMiddleware(ABC):
    """the base for chat command middleware, extend from this when implementing your own"""

    @abstractmethod
    async def can_execute(self, command: ChatCommand) -> bool:
        """return :code:`True` if the given command should execute, otherwise :code:`False`"""
        pass


class ChannelRestriction(BaseCommandMiddleware):
    """Filters in which channels a command can be executed in"""

    def __init__(self,
                 allowed_channel: Optional[List[str]] = None,
                 denied_channel: Optional[List[str]] = None):
        """
        :param allowed_channel: if provided, the command can only be used in channels on this list
        :param denied_channel:  if provided, the command can't be used in channels on this list
        """
        self.allowed = allowed_channel if allowed_channel is not None else []
        self.denied = denied_channel if denied_channel is not None else []

    async def can_execute(self, command: ChatCommand) -> bool:
        if len(self.allowed) > 0:
            if command.room.name not in self.allowed:
                return False
        return command.room.name not in self.denied


class UserRestriction(BaseCommandMiddleware):
    """Filters which users can execute a command"""

    def __init__(self,
                 allowed_users: Optional[List[str]] = None,
                 denied_users: Optional[List[str]] = None):
        """
        :param allowed_users: if provided, the command can only be used by one of the provided users
        :param denied_users: if provided, the command can not be used by any of the provided users
        """
        self.allowed = allowed_users if allowed_users is not None else []
        self.denied = denied_users if denied_users is not None else []

    async def can_execute(self, command: ChatCommand) -> bool:
        if len(self.allowed) > 0:
            if command.user.name not in self.allowed:
                return False
        return command.user.name not in self.denied


class StreamerOnly(BaseCommandMiddleware):
    """Restricts the use of commands to only the streamer in their channel"""

    async def can_execute(self, command: ChatCommand) -> bool:
        return command.room.name == command.user.name
