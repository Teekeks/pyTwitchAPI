#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
"""
Twitch Chat Bot
---------------

A simple twitch chat bot.\n
Chat bots can join channels, listen to chat and reply to messages, commands, subscriptions and many more.


********
Commands
********

Chat commands are specific messages user can send in chat in order to trigger some action of your bot.

Example:

.. code-block::

    <User123>: !say Hello world
    <MyBot>: User123 asked me to say "Hello world"


You can register listeners to chat commands using :const:`~twitchAPI.chat.Chat.register_command()`.

The bot prefix can be set by using :const:`~twitchAPI.chat.Chat.set_prefix()`, the default is :code:`!`

Your command listener function needs to be async and take in one parameter of type :const:`~twitchAPI.chat.ChatCommand`.

Example:

.. code-block:: python

    async def say_command_handler(cmd: ChatCommand):
        await cmd.reply(f'{cmd.user.name} asked me to say "{cmd.parameter}")

    chat.register_command('say', say_command_handler)

******************
Command Middleware
******************

Command Middleware is a way to control when a command should be executed.

See :doc:`/modules/twitchAPI.chat.middleware` and :doc:`/tutorial/chat-use-middleware` for more information.

******
Events
******

You can listen to different events happening in the chat rooms you joined.

Generally you register a event listener using :const:`~twitchAPI.chat.Chat.register_event()`.
The first parameter has to be of type :const:`~twitchAPI.type.ChatEvent` and the second one is your listener function.

Those Listeners always have to be async functions taking in one parameter (the payload). The Payload type is described below.

Example:

.. code-block:: python

    async def on_ready(cmd: EventData):
        await cmd.chat.join_room('teekeks42')

    chat.register_event(ChatEvent.READY, on_ready)

Available Events
================

.. list-table::
   :header-rows: 1

   * - Event Name
     - Event Data
     - Description
   * - Bot Ready
     - ChatEvent: :obj:`~twitchAPI.type.ChatEvent.READY` |br|
       Payload: :const:`~twitchAPI.chat.EventData`
     - This Event is triggered when the bot is started up and ready to join channels.
   * - Message Send
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.MESSAGE` |br|
       Payload: :const:`~twitchAPI.chat.ChatMessage`
     - This Event is triggered when someone wrote a message in a channel we joined
   * - Channel Subscription
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.SUB` |br|
       Payload: :const:`~twitchAPI.chat.ChatSub`
     - This Event is triggered when someone subscribed to a channel we joined.
   * - Raid
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.RAID` |br|
       Payload: :const:`dict`
     - Triggered when a channel gets raided
   * - Channel Config Changed
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.ROOM_STATE_CHANGE` |br|
       Payload: :const:`~twitchAPI.chat.RoomStateChangeEvent`
     - Triggered when a channel is changed (e.g. sub only mode was enabled)
   * - User Channel Join
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.JOIN` |br|
       Payload: :const:`~twitchAPI.chat.JoinEvent`
     - Triggered when someone other than the bot joins a channel. |br| **This will not always trigger, depending on channel size**
   * - User Channel Leave
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.USER_LEFT` |br|
       Payload: :const:`~twitchAPI.chat.LeftEvent`
     - Triggered when someone other than the bot leaves a channel. |br| **This will not always trigger, depending on channel size**
   * - Bot Channel Join
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.JOINED` |br|
       Payload: :const:`~twitchAPI.chat.JoinedEvent`
     - Triggered when the bot joins a channel
   * - Bot Channel Leave
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.LEFT` |br|
       Payload: :const:`~twitchAPI.chat.LeftEvent`
     - Triggered when the bot left a channel
   * - Message Delete
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.MESSAGE_DELETE` |br|
       Payload: :const:`~twitchAPI.chat.MessageDeletedEvent`
     - Triggered when a single message in a channel got deleted
   * - User Messages Cleared
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.CHAT_CLEARED` |br|
       Payload: :const:`~twitchAPI.chat.ClearChatEvent`
     - Triggered when a user was banned, timed out and/or all messaged from a user where deleted
   * - Bot Receives Whisper Message
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.WHISPER` |br|
       Payload: :const:`~twitchAPI.chat.WhisperEvent`
     - Triggered when someone whispers to your bot. |br| **You need the** :const:`~twitchAPI.type.AuthScope.WHISPERS_READ` **Auth Scope to receive this Event.**
   * - Server Notice
     - ChatEvent: :const:`~twitchAPI.type.ChatEvent.NOTICE` |br|
       Payload: :const:`~twitchAPI.chat.NoticeEvent`
     - Triggered when server sends a notice message.


************
Code example
************

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope, ChatEvent
    from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
    import asyncio

    APP_ID = 'my_app_id'
    APP_SECRET = 'my_app_secret'
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
    TARGET_CHANNEL = 'teekeks42'


    # this will be called when the event READY is triggered, which will be on bot start
    async def on_ready(ready_event: EventData):
        print('Bot is ready for work, joining channels')
        # join our target channel, if you want to join multiple, either call join for each individually
        # or even better pass a list of channels as the argument
        await ready_event.chat.join_room(TARGET_CHANNEL)
        # you can do other bot initialization things in here


    # this will be called whenever a message in a channel was send by either the bot OR another user
    async def on_message(msg: ChatMessage):
        print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')


    # this will be called whenever someone subscribes to a channel
    async def on_sub(sub: ChatSub):
        print(f'New subscription in {sub.room.name}:\\n'
              f'  Type: {sub.sub_plan}\\n'
              f'  Message: {sub.sub_message}')


    # this will be called whenever the !reply command is issued
    async def test_command(cmd: ChatCommand):
        if len(cmd.parameter) == 0:
            await cmd.reply('you did not tell me what to reply with')
        else:
            await cmd.reply(f'{cmd.user.name}: {cmd.parameter}')


    # this is where we set up the bot
    async def run():
        # set up twitch api instance and add user authentication with some scopes
        twitch = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(twitch, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

        # create chat instance
        chat = await Chat(twitch)

        # register the handlers for the events you want

        # listen to when the bot is done starting up and ready to join channels
        chat.register_event(ChatEvent.READY, on_ready)
        # listen to chat messages
        chat.register_event(ChatEvent.MESSAGE, on_message)
        # listen to channel subscriptions
        chat.register_event(ChatEvent.SUB, on_sub)
        # there are more events, you can view them all in this documentation

        # you can directly register commands and their handlers, this will register the !reply command
        chat.register_command('reply', test_command)


        # we are done with our setup, lets start this bot up!
        chat.start()

        # lets run till we press enter in the console
        try:
            input('press ENTER to stop\\n')
        finally:
            # now we can close the chat bot and the twitch api client
            chat.stop()
            await twitch.close()


    # lets run our setup
    asyncio.run(run())

*******************
Class Documentation
*******************
"""
import asyncio
import dataclasses
import datetime
import re
import threading
from asyncio import CancelledError
from functools import partial
from logging import getLogger, Logger
from time import sleep
import aiohttp


from twitchAPI.twitch import Twitch
from twitchAPI.object.api import TwitchUser
from twitchAPI.helper import TWITCH_CHAT_URL, first, RateLimitBucket, RATE_LIMIT_SIZES, done_task_callback
from twitchAPI.type import ChatRoom, TwitchBackendException, AuthType, AuthScope, ChatEvent, UnauthorizedException

from typing import List, Optional, Union, Callable, Dict, Awaitable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from twitchAPI.chat.middleware import BaseCommandMiddleware


__all__ = ['Chat', 'ChatUser', 'EventData', 'ChatMessage', 'ChatCommand', 'ChatSub', 'ChatRoom', 'ChatEvent', 'RoomStateChangeEvent',
           'JoinEvent', 'JoinedEvent', 'LeftEvent', 'ClearChatEvent', 'WhisperEvent', 'MessageDeletedEvent', 'NoticeEvent', 'HypeChat']


class ChatUser:
    """Represents a user in a chat channel
    """

    def __init__(self, chat, parsed, name_override=None):
        self.chat: 'Chat' = chat
        """The :const:`twitchAPI.chat.Chat` instance"""
        self.name: str = parsed['source']['nick'] if parsed['source']['nick'] is not None else f'{chat.username}'
        """The name of the user"""
        if self.name[0] == ':':
            self.name = self.name[1:]
        if name_override is not None:
            self.name = name_override
        self.badge_info = parsed['tags'].get('badge-info')
        """All infos related to the badges of the user"""
        self.badges = parsed['tags'].get('badges')
        """The badges of the user"""
        self.source_badges = parsed['tags'].get('source-badges')
        """The badges for the chatter in the room the message was sent from. This uses the same format as the badges tag."""
        self.source_badge_info = parsed['tags'].get('source-badge-info')
        """Contains metadata related to the chat badges in the source-badges tag."""
        self.color: str = parsed['tags'].get('color')
        """The color of the chat user if set"""
        self.display_name: str = parsed['tags'].get('display-name')
        """The display name, should usually be the same as name"""
        self.mod: bool = parsed['tags'].get('mod', '0') == '1'
        """if the user is a mod in chat channel"""
        self.subscriber: bool = parsed['tags'].get('subscriber') == '1'
        """if the user is a subscriber to the channel"""
        self.turbo: bool = parsed['tags'].get('turbo') == '1'
        """Indicates whether the user has site-wide commercial free mode enabled"""
        self.id: str = parsed['tags'].get('user-id')
        """The ID of the user"""
        self.user_type: str = parsed['tags'].get('user-type')
        """The type of user"""
        self.vip: bool = parsed['tags'].get('vip') == '1'
        """if the chatter is a channel VIP"""


class EventData:
    """Represents a basic chat event"""

    def __init__(self, chat):
        self.chat: 'Chat' = chat
        """The :const:`twitchAPI.chat.Chat` instance"""


class MessageDeletedEvent(EventData):

    def __init__(self, chat, parsed):
        super(MessageDeletedEvent, self).__init__(chat)
        self._room_name = parsed['command']['channel'][1:]
        self.message: str = parsed['parameters']
        """The content of the message that got deleted"""
        self.user_name: str = parsed['tags'].get('login')
        """Username of the message author"""
        self.message_id: str = parsed['tags'].get('target-msg-id')
        """ID of the message that got deleted"""
        self.sent_timestamp: int = int(parsed['tags'].get('tmi-sent-ts'))
        """The timestamp the deleted message was send"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """The room the message was deleted in"""
        return self.chat.room_cache.get(self._room_name)


class RoomStateChangeEvent(EventData):
    """Triggered when a room state changed"""

    def __init__(self, chat, prev, new):
        super(RoomStateChangeEvent, self).__init__(chat)
        self.old: Optional[ChatRoom] = prev
        """The State of the room from before the change, might be Null if not in cache"""
        self.new: ChatRoom = new
        """The new room state"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """Returns the Room from cache"""
        return self.chat.room_cache.get(self.new.name)


class JoinEvent(EventData):
    """"""

    def __init__(self, chat, channel_name, user_name):
        super(JoinEvent, self).__init__(chat)
        self._name = channel_name
        self.user_name: str = user_name
        """The name of the user that joined"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """The room the user joined to"""
        return self.chat.room_cache.get(self._name)


class JoinedEvent(EventData):
    """"""

    def __init__(self, chat, channel_name, user_name):
        super(JoinedEvent, self).__init__(chat)
        self.room_name: str = channel_name
        """the name of the room the bot joined to"""
        self.user_name: str = user_name
        """the name of the bot"""


class LeftEvent(EventData):
    """When the bot or a user left a room"""

    def __init__(self, chat, channel_name, room, user):
        super(LeftEvent, self).__init__(chat)
        self.room_name: str = channel_name
        """the name of the channel the bot left"""
        self.user_name: str = user
        """The name of the user that left the chat"""
        self.cached_room: Optional[ChatRoom] = room
        """the cached room state, might bo Null"""


class HypeChat:

    def __init__(self, parsed):
        self.amount: int = int(parsed['tags'].get('pinned-chat-paid-amount'))
        """The value of the Hype Chat sent by the user."""
        self.currency: str = parsed['tags'].get('pinned-chat-paid-currency')
        """The ISO 4217 alphabetic currency code the user has sent the Hype Chat in."""
        self.exponent: int = int(parsed['tags'].get('pinned-chat-paid-exponent'))
        """Indicates how many decimal points this currency represents partial amounts in. 
        Decimal points start from the right side of the value defined in :const:`~twitchAPI.chat.HypeChat.amount`"""
        self.level: str = parsed['tags'].get('pinned-chat-paid-level')
        """The level of the Hype Chat, in English.\n
        Possible Values are:
        :code:`ONE`, :code:`TWO`, :code:`THREE`, :code:`FOUR`, :code:`FIVE`, :code:`SIX`, :code:`SEVEN`, :code:`EIGHT`, :code:`NINE`, :code:`TEN`"""
        self.is_system_message: bool = parsed['tags'].get('pinned-chat-paid-is-system-message') == '1'
        """A Boolean value that determines if the message sent with the Hype Chat was filled in by the system.\n
           If True, the user entered no message and the body message was automatically filled in by the system.\n
           If False, the user provided their own message to send with the Hype Chat."""


class ChatMessage(EventData):
    """Represents a chat message"""

    def __init__(self, chat, parsed):
        super(ChatMessage, self).__init__(chat)
        self._parsed = parsed
        self.text: str = parsed['parameters']
        """The message"""
        self.is_me: bool = False
        """Flag indicating if the message used the /me command"""
        result = _ME_REGEX.match(self.text)
        if result is not None:
            self.text = result.group('msg')
            self.is_me = True
        self.bits: int = int(parsed['tags'].get('bits', '0'))
        """The amount of Bits the user cheered"""
        self.first: bool = parsed['tags'].get('first-msg', '0') != '0'
        """Flag if message is user's first ever in room"""
        self.sent_timestamp: int = int(parsed['tags'].get('tmi-sent-ts'))
        """the unix timestamp of when the message was sent"""
        self.reply_parent_msg_id: Optional[str] = parsed['tags'].get('reply-parent-msg-id')
        """An ID that uniquely identifies the parent message that this message is replying to."""
        self.reply_parent_user_id: Optional[str] = parsed['tags'].get('reply-parent-user-id')
        """An ID that identifies the sender of the parent message."""
        self.reply_parent_user_login: Optional[str] = parsed['tags'].get('reply-parent-user-login')
        """The login name of the sender of the parent message. """
        self.reply_parent_display_name: Optional[str] = parsed['tags'].get('reply-parent-display-name')
        """The display name of the sender of the parent message."""
        self.reply_parent_msg_body: Optional[str] = parsed['tags'].get('reply-parent-msg-body')
        """The text of the parent message"""
        self.reply_thread_parent_msg_id: Optional[str] = parsed['tags'].get('reply-thread-parent-msg-id')
        """An ID that uniquely identifies the top-level parent message of the reply thread that this message is replying to.
           Is :code:`None` if this message is not a reply."""
        self.reply_thread_parent_user_login: Optional[str] = parsed['tags'].get('reply-thread-parent-user-login')
        """The login name of the sender of the top-level parent message. Is :code:`None` if this message is not a reply."""
        self.emotes = parsed['tags'].get('emotes')
        """The emotes used in the message"""
        self.id: str = parsed['tags'].get('id')
        """the ID of the message"""
        self.hype_chat: Optional[HypeChat] = HypeChat(parsed) if parsed['tags'].get('pinned-chat-paid-level') is not None else None
        """Hype Chat related data, is None if the message was not a hype chat"""
        self.source_id: Optional[str] = parsed['tags'].get('source-id')
        """A UUID that identifies the source message from the channel the message was sent from."""
        self.source_room_id: Optional[str] = parsed['tags'].get('source-room-id')
        """An ID that identifies the chat room (channel) the message was sent from."""



    @property
    def room(self) -> Optional[ChatRoom]:
        """The channel the message was issued in"""
        return self.chat.room_cache.get(self._parsed['command']['channel'][1:])

    @property
    def user(self) -> ChatUser:
        """The user that issued the message"""
        return ChatUser(self.chat, self._parsed)

    async def reply(self, text: str):
        """Reply to this message"""
        bucket = self.chat._get_message_bucket(self._parsed['command']['channel'][1:])
        await bucket.put()
        await self.chat.send_raw_irc_message(f'@reply-parent-msg-id={self.id} PRIVMSG #{self.room.name} :{text}')


class ChatCommand(ChatMessage):
    """Represents a command"""

    def __init__(self, chat, parsed):
        super(ChatCommand, self).__init__(chat, parsed)
        self.name: str = parsed['command'].get('bot_command')
        """the name of the command"""
        self.parameter: str = parsed['command'].get('bot_command_params', '')
        """the parameter given to the command"""

    async def send(self, message: str):
        """Sends a message to the channel the command was issued in

        :param message: the message you want to send
        """
        await self.chat.send_message(self.room.name, message)


class ChatSub:
    """Represents a sub to a channel"""

    def __init__(self, chat, parsed):
        self.chat: 'Chat' = chat
        """The :const:`twitchAPI.chat.Chat` instance"""
        self._parsed = parsed
        self.sub_type: str = parsed['tags'].get('msg-id')
        """The type of sub given"""
        self.sub_message: str = parsed['parameters'] if parsed['parameters'] is not None else ''
        """The message that was sent together with the sub"""
        self.sub_plan: str = parsed['tags'].get('msg-param-sub-plan')
        """the ID of the subscription plan that was used"""
        self.sub_plan_name: str = parsed['tags'].get('msg-param-sub-plan-name')
        """the name of the subscription plan that was used"""
        self.system_message: str = parsed['tags'].get('system-msg', '').replace('\\\\s', ' ')
        """the system message that was generated for this sub"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """The room this sub was issued in"""
        return self.chat.room_cache.get(self._parsed['command']['channel'][1:])


class ClearChatEvent(EventData):

    def __init__(self, chat, parsed):
        super(ClearChatEvent, self).__init__(chat)
        self.room_name: str = parsed['command']['channel'][1:]
        """The name of the chat room the event happened in"""
        self.room_id: str = parsed['tags'].get('room-id')
        """The ID of the chat room the event happened in"""
        self.user_name: str = parsed['parameters']
        """The name of the user who's messages got cleared"""
        self.duration: Optional[int] = int(parsed['tags']['ban-duration']) if parsed['tags'].get('ban-duration') not in (None, '') else None
        """duration of the timeout in seconds. None if user was not timed out"""
        self.banned_user_id: Optional[str] = parsed['tags'].get('target-user-id')
        """The ID of the user who got banned or timed out. if :const:`~twitchAPI.chat.ClearChatEvent.duration` is None, the user was banned.
        Will be None when the user was not banned nor timed out."""
        self.sent_timestamp: int = int(parsed['tags'].get('tmi-sent-ts'))
        """The timestamp the event happened at"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """The room this event was issued in. None on cache miss."""
        return self.chat.room_cache.get(self.room_name)


class WhisperEvent(EventData):

    def __init__(self, chat, parsed):
        super(WhisperEvent, self).__init__(chat)
        self._parsed = parsed
        self.message: str = parsed['parameters']
        """The message that was send"""

    @property
    def user(self) -> ChatUser:
        """The user that DMed your bot"""
        return ChatUser(self.chat, self._parsed)


class NoticeEvent(EventData):
    """Represents a server notice"""

    def __init__(self, chat, parsed):
        super(NoticeEvent, self).__init__(chat)
        self._room_name = parsed['command']['channel'][1:]
        """The name of the chat room the notice is from"""
        self.msg_id: str = parsed['tags'].get('msg-id')
        """Message ID of the notice, `Msg-id reference <https://dev.twitch.tv/docs/irc/msg-id/>`__"""
        self.message: str = parsed['parameters']
        """Description for the msg_id"""

    @property
    def room(self) -> Optional[ChatRoom]:
        """The room this notice is from"""
        return self.chat.room_cache.get(self._room_name)


COMMAND_CALLBACK_TYPE = Callable[[ChatCommand], Awaitable[None]]
EVENT_CALLBACK_TYPE = Callable[[Any], Awaitable[None]]
CHATROOM_TYPE = Union[str, ChatRoom]

_ME_REGEX = re.compile(r'^\x01ACTION (?P<msg>.+)\x01$')


class Chat:
    """The chat bot instance"""

    def __init__(self,
                 twitch: Twitch,
                 connection_url: Optional[str] = None,
                 is_verified_bot: bool = False,
                 initial_channel: Optional[List[str]] = None,
                 callback_loop: Optional[asyncio.AbstractEventLoop] = None,
                 no_message_reset_time: Optional[float] = 10,
                 no_shared_chat_messages: bool = True):
        """
        :param twitch: A Authenticated twitch instance
        :param connection_url: alternative connection url |default|:code:`None`
        :param is_verified_bot: set to true if your bot is verified by twitch |default|:code:`False`
        :param initial_channel: List of channel which should be automatically joined on startup |default| :code:`None`
        :param callback_loop: The asyncio eventloop to be used for callbacks. \n
            Set this if you or a library you use cares about which asyncio event loop is running the callbacks.
            Defaults to the one used by Chat.
        :param no_message_reset_time: How many minutes of mo messages from Twitch before the connection is considered
            dead. Twitch sends a PING just under every 5 minutes and the bot must respond to them for Twitch to keep
            the connection active. At 10 minutes we've definitely missed at least one PING |default|:code:`10`
        :param no_shared_chat_messages: Filter out Twitch shared chat messages from other channels. This will only
            listen for messages that were sent in the chat room that the bot is listening in.
        """
        self.logger: Logger = getLogger('twitchAPI.chat')
        """The logger used for Chat related log messages"""
        self._prefix: str = "!"
        self.twitch: Twitch = twitch
        """The twitch instance being used"""
        if not self.twitch.has_required_auth(AuthType.USER, [AuthScope.CHAT_READ]):
            raise ValueError('passed twitch instance is missing User Auth.')
        self.connection_url: str = connection_url if connection_url is not None else TWITCH_CHAT_URL
        """Alternative connection url |default|:code:`None`"""
        self.ping_frequency: int = 120
        """Frequency in seconds for sending ping messages. This should usually not be changed."""
        self.ping_jitter: int = 4
        """Jitter in seconds for ping messages. This should usually not be changed."""
        self._callback_loop = callback_loop
        self.no_message_reset_time: Optional[float] = no_message_reset_time
        self.no_shared_chat_messages: bool = no_shared_chat_messages
        self.listen_confirm_timeout: int = 30
        """Time in second that any :code:`listen_` should wait for its subscription to be completed."""
        self.reconnect_delay_steps: List[int] = [0, 1, 2, 4, 8, 16, 32, 64, 128]
        """Time in seconds between reconnect attempts"""
        self.log_no_registered_command_handler: bool = True
        """Controls if instances of commands being issued in chat where no handler exists should be logged. |default|:code:`True`"""
        self.__connection = None
        self._session = None
        self.__socket_thread: Optional[threading.Thread] = None
        self.__running: bool = False
        self.__socket_loop = None
        self.__startup_complete: bool = False
        self.__tasks = None
        self._ready = False
        self._send_buckets = {}
        self._join_target = [c[1:].lower() if c[0] == '#' else c.lower() for c in initial_channel] if initial_channel is not None else []
        self._join_bucket = RateLimitBucket(10, 2000 if is_verified_bot else 20, 'channel_join', self.logger)
        self.__waiting_for_pong: bool = False
        self._event_handler = {}
        self._command_handler = {}
        self.room_cache: Dict[str, ChatRoom] = {}
        """internal cache of all chat rooms the bot is currently in"""
        self._room_join_locks = []
        self._room_leave_locks = []
        self._closing: bool = False
        self.join_timeout: int = 10
        """Time in seconds till a channel join attempt times out"""
        self._mod_status_cache = {}
        self._subscriber_status_cache = {}
        self._channel_command_prefix = {}
        self._command_middleware: List['BaseCommandMiddleware'] = []
        self._command_specific_middleware: Dict[str, List['BaseCommandMiddleware']] = {}
        self._task_callback = partial(done_task_callback, self.logger)
        self.default_command_execution_blocked_handler: Optional[Callable[[ChatCommand], Awaitable[None]]] = None
        """The default handler to be called should a command execution be blocked by a middleware that has no specific handler set."""
        self.username: Optional[str] = None

    def __await__(self):
        t = asyncio.create_task(self._get_username())
        yield from t
        return self

    async def _get_username(self):
        user: TwitchUser = await first(self.twitch.get_users())
        self.username = user.login.lower()

    ##################################################################################################################################################
    # command parsing
    ##################################################################################################################################################

    def _parse_irc_message(self, message: str):
        parsed_message = {
            'tags': {},
            'source': None,
            'command': None,
            'parameters': None
        }
        idx = 0
        raw_tags_component = None
        raw_source_component = None
        raw_parameters_component = None

        if message[idx] == '@':
            end_idx = message.index(' ')
            raw_tags_component = message[1:end_idx]
            idx = end_idx + 1

        if message[idx] == ':':
            end_idx = message.index(' ', idx)
            raw_source_component = message[idx:end_idx]
            idx = end_idx + 1

        try:
            end_idx = message.index(':', idx)
        except ValueError:
            end_idx = len(message)

        raw_command_component = message[idx:end_idx].strip()

        if end_idx != len(message):
            idx = end_idx + 1
            raw_parameters_component = message[idx::]

        parsed_message['command'] = self._parse_irc_command(raw_command_component)

        if parsed_message['command'] is None:
            return None

        if raw_tags_component is not None:
            parsed_message['tags'] = self._parse_irc_tags(raw_tags_component)

        parsed_message['source'] = self._parse_irc_source(raw_source_component)
        parsed_message['parameters'] = raw_parameters_component
        if parsed_message['command']['command'] == 'PRIVMSG':
            ch = parsed_message['command'].get('channel', '#')[1::]
            used_prefix = self._channel_command_prefix.get(ch, self._prefix)
            if raw_parameters_component is not None and raw_parameters_component.startswith(used_prefix):
                parsed_message['command'] = self._parse_irc_parameters(raw_parameters_component, parsed_message['command'], used_prefix)

        return parsed_message

    @staticmethod
    def _parse_irc_parameters(raw_parameters_component: str, command, prefix):
        command_parts = raw_parameters_component[len(prefix)::].strip()
        try:
            params_idx = command_parts.index(' ')
        except ValueError:
            command['bot_command'] = command_parts
            return command
        command['bot_command'] = command_parts[:params_idx]
        command['bot_command_params'] = command_parts[params_idx:].strip()
        return command

    @staticmethod
    def _parse_irc_source(raw_source_component: str):
        if raw_source_component is None:
            return None
        source_parts = raw_source_component.split('!')
        return {
            'nick': source_parts[0] if len(source_parts) == 2 else None,
            'host': source_parts[1] if len(source_parts) == 2 else source_parts[0]
        }

    @staticmethod
    def _parse_irc_tags(raw_tags_component: str):
        tags_to_ignore = ('client-nonce', 'flags')
        parsed_tags = {}

        tags = raw_tags_component.split(';')

        for tag in tags:
            parsed_tag = tag.split('=')
            tag_value = None if parsed_tag[1] == '' else parsed_tag[1]
            if parsed_tag[0] in ('badges', 'badge-info', 'source-badges', 'source-badge-info'):
                if tag_value is not None:
                    d = {}
                    badges = tag_value.split(',')
                    for pair in badges:
                        badge_parts = pair.split('/', 1)
                        d[badge_parts[0]] = badge_parts[1]
                    parsed_tags[parsed_tag[0]] = d
                else:
                    parsed_tags[parsed_tag[0]] = None
            elif parsed_tag[0] == 'emotes':
                if tag_value is not None:
                    d = {}
                    emotes = tag_value.split('/')
                    for emote in emotes:
                        emote_parts = emote.split(':')
                        text_positions = []
                        positions = emote_parts[1].split(',')
                        for position in positions:
                            pos_parts = position.split('-')
                            text_positions.append({
                                'start_position': pos_parts[0],
                                'end_position': pos_parts[1]
                            })
                        d[emote_parts[0]] = text_positions
                    parsed_tags[parsed_tag[0]] = d
                else:
                    parsed_tags[parsed_tag[0]] = None
            elif parsed_tag[0] == 'emote-sets':
                parsed_tags[parsed_tag[0]] = tag_value.split(',')
            else:
                if parsed_tag[0] not in tags_to_ignore:
                    parsed_tags[parsed_tag[0]] = tag_value
        return parsed_tags

    def _parse_irc_command(self, raw_command_component: str):
        command_parts = raw_command_component.split(' ')

        if command_parts[0] in ('JOIN', 'PART', 'NOTICE', 'CLEARCHAT', 'HOSTTARGET', 'PRIVMSG',
                                'USERSTATE', 'ROOMSTATE', '001', 'USERNOTICE', 'CLEARMSG', 'WHISPER'):
            parsed_command = {
                'command': command_parts[0],
                'channel': command_parts[1]
            }
        elif command_parts[0] in ('PING', 'GLOBALUSERSTATE', 'RECONNECT'):
            parsed_command = {
                'command': command_parts[0]
            }
        elif command_parts[0] == 'CAP':
            parsed_command = {
                'command': command_parts[0],
                'is_cap_request_enabled': command_parts[2] == 'ACK'
            }
        elif command_parts[0] == '421':
            # unsupported command in parts 2
            self.logger.warning(f'Unsupported IRC command: {command_parts[0]}')
            return None
        elif command_parts[0] == '353':
            parsed_command = {
                'command': command_parts[0]
            }
        elif command_parts[0] in ('002', '003', '004', '366', '372', '375', '376'):
            self.logger.debug(f'numeric message: {command_parts[0]}\n{raw_command_component}')
            return None
        else:
            # unexpected command
            self.logger.warning(f'Unexpected command: {command_parts[0]}')
            return None

        return parsed_command

    ##################################################################################################################################################
    # general web socket tools
    ##################################################################################################################################################

    def start(self) -> None:
        """
        Start the Chat Client

        :raises RuntimeError: if already started
        """
        self.logger.debug('starting chat...')
        if self.__running:
            raise RuntimeError('already started')
        if self.username is None:
            raise RuntimeError('Chat() was not awaited')
        if not self.twitch.has_required_auth(AuthType.USER, [AuthScope.CHAT_READ]):
            raise UnauthorizedException('CHAT_READ authscope is required to run a chat bot')
        self.__startup_complete = False
        self._closing = False
        self._ready = False
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
        while not self.__startup_complete:
            sleep(0.01)
        self.logger.debug('chat started up!')

    def stop(self) -> None:
        """
        Stop the Chat Client

        :raises RuntimeError: if the client is not running
        """

        if not self.__running:
            raise RuntimeError('not running')
        self.logger.debug('stopping chat...')
        self.__startup_complete = False
        self.__running = False
        self._ready = False
        f = asyncio.run_coroutine_threadsafe(self._stop(), self.__socket_loop)
        f.result()

    async def _stop(self):
        await self.__connection.close()
        await self._session.close()
        # wait for ssl to close as per aiohttp docs...
        await asyncio.sleep(0.25)
        # clean up bot state
        self.__connection = None
        self._session = None
        self.room_cache = {}
        self._room_join_locks = []
        self._room_leave_locks = []
        self._closing = True

    async def __connect(self, is_startup=False):
        if is_startup:
            self.logger.debug('connecting...')
        else:
            self.logger.debug('reconnecting...')
        if self.__connection is not None and not self.__connection.closed:
            await self.__connection.close()
        retry = 0
        need_retry = True
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.twitch.session_timeout)
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self.__connection = await self._session.ws_connect(self.connection_url)
            except Exception:
                self.logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]}s...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException('can\'t connect')

    async def _keep_loop_alive(self):
        while not self._closing:
            await asyncio.sleep(0.1)

    def __run_socket(self):
        self.__socket_loop = asyncio.new_event_loop()
        if self._callback_loop is None:
            self._callback_loop = self.__socket_loop
        asyncio.set_event_loop(self.__socket_loop)

        # startup
        self.__socket_loop.run_until_complete(self.__connect(is_startup=True))

        self.__tasks = [
            asyncio.ensure_future(self.__task_receive(), loop=self.__socket_loop),
            asyncio.ensure_future(self.__task_startup(), loop=self.__socket_loop)
        ]
        # keep loop alive
        self.__socket_loop.run_until_complete(self._keep_loop_alive())

    async def _send_message(self, message: str):
        self.logger.debug(f'> "{message}"')
        await self.__connection.send_str(message)

    async def __task_receive(self):
        receive_timeout = None if self.no_message_reset_time is None else self.no_message_reset_time * 60
        try:
            handlers: Dict[str, Callable] = {
                'PING': self._handle_ping,
                'PRIVMSG': self._handle_msg,
                '001': self._handle_ready,
                'ROOMSTATE': self._handle_room_state,
                'JOIN': self._handle_join,
                'USERNOTICE': self._handle_user_notice,
                'CLEARMSG': self._handle_clear_msg,
                'CAP': self._handle_cap_reply,
                'PART': self._handle_part,
                'NOTICE': self._handle_notice,
                'CLEARCHAT': self._handle_clear_chat,
                'WHISPER': self._handle_whisper,
                'RECONNECT': self._handle_reconnect,
                'USERSTATE': self._handle_user_state
            }
            while not self.__connection.closed:
                try:  # At minimum we should receive a PING request just under every 5 minutes
                    message = await self.__connection.receive(timeout=receive_timeout)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Reached timeout for websocket receive, will attempt a reconnect")
                    if self.__running:
                        try:
                            await self._handle_base_reconnect()
                        except TwitchBackendException:
                            self.logger.exception('Connection to chat websocket lost and unable to reestablish connection!')
                            break
                    else:
                        break
                if message.type == aiohttp.WSMsgType.TEXT:
                    messages = message.data.split('\r\n')
                    for m in messages:
                        if len(m) == 0:
                            continue
                        self.logger.debug(f'< {m}')
                        parsed = self._parse_irc_message(m)
                        # a message we don't know or don't care about
                        if parsed is None:
                            continue
                        handler = handlers.get(parsed['command']['command'])
                        if handler is not None:
                            asyncio.ensure_future(handler(parsed))
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.debug('websocket is closing')
                    if self.__running:
                        try:
                            await self._handle_base_reconnect()
                        except TwitchBackendException:
                            self.logger.exception('Connection to chat websocket lost and unable to reestablish connection!')
                            break
                    else:
                        break
                elif message.type == aiohttp.WSMsgType.ERROR:
                    self.logger.warning('error in websocket: ' + str(self.__connection.exception()))
                    break
        except CancelledError:
            # we are closing down!
            # print('we are closing down!')
            return

    async def _handle_base_reconnect(self):
        await self.__connect(is_startup=False)
        await self.__task_startup()

    # noinspection PyUnusedLocal
    async def _handle_reconnect(self, parsed: dict):
        self.logger.info('got reconnect request...')
        await self._handle_base_reconnect()
        self.logger.info('reconnect completed')

    async def _handle_whisper(self, parsed: dict):
        e = WhisperEvent(self, parsed)
        for handler in self._event_handler.get(ChatEvent.WHISPER, []):
            t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)

    async def _handle_clear_chat(self, parsed: dict):
        e = ClearChatEvent(self, parsed)
        for handler in self._event_handler.get(ChatEvent.CHAT_CLEARED, []):
            t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)

    async def _handle_notice(self, parsed: dict):
        e = NoticeEvent(self, parsed)
        for handler in self._event_handler.get(ChatEvent.NOTICE, []):
            t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)
        self.logger.debug(f'got NOTICE for channel {parsed["command"]["channel"]}: {parsed["tags"].get("msg-id")}')

    async def _handle_clear_msg(self, parsed: dict):
        ev = MessageDeletedEvent(self, parsed)
        for handler in self._event_handler.get(ChatEvent.MESSAGE_DELETE, []):
            t = asyncio.ensure_future(handler(ev), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)

    async def _handle_cap_reply(self, parsed: dict):
        self.logger.debug(f'got CAP reply, granted caps: {parsed["parameters"]}')
        caps = parsed['parameters'].split()
        if not all([x in caps for x in ['twitch.tv/membership', 'twitch.tv/tags', 'twitch.tv/commands']]):
            self.logger.warning(f'chat bot did not get all requested capabilities granted, this might result in weird bot behavior!')

    async def _handle_join(self, parsed: dict):
        ch = parsed['command']['channel'][1:]
        nick = parsed['source']['nick'][1:]
        if ch in self._room_join_locks and nick == self.username:
            self._room_join_locks.remove(ch)
        if nick == self.username:
            e = JoinedEvent(self, ch, nick)
            for handler in self._event_handler.get(ChatEvent.JOINED, []):
                t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)
        else:
            e = JoinEvent(self, ch, nick)
            for handler in self._event_handler.get(ChatEvent.JOIN, []):
                t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)

    async def _handle_part(self, parsed: dict):
        ch = parsed['command']['channel'][1:]
        usr = parsed['source']['nick'][1:]
        if usr == self.username:
            if ch in self._room_leave_locks:
                self._room_leave_locks.remove(ch)
            room = self.room_cache.pop(ch, None)
            e = LeftEvent(self, ch, room, usr)
            for handler in self._event_handler.get(ChatEvent.LEFT, []):
                t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)
        else:
            room = self.room_cache.get(ch)
            e = LeftEvent(self, ch, room, usr)
            for handler in self._event_handler.get(ChatEvent.USER_LEFT, []):
                t = asyncio.ensure_future(handler(e), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)

    async def _handle_user_notice(self, parsed: dict):
        if parsed['tags'].get('msg-id') == 'raid':
            handlers = self._event_handler.get(ChatEvent.RAID, [])
            for handler in handlers:
                asyncio.ensure_future(handler(parsed))
        elif parsed['tags'].get('msg-id') in ('sub', 'resub', 'subgift'):
            sub = ChatSub(self, parsed)
            for handler in self._event_handler.get(ChatEvent.SUB, []):
                t = asyncio.ensure_future(handler(sub), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)

    async def _handle_room_state(self, parsed: dict):
        self.logger.debug('got room state event')
        state = ChatRoom(
            name=parsed['command']['channel'][1:],
            is_emote_only=parsed['tags'].get('emote-only') == '1',
            is_subs_only=parsed['tags'].get('subs-only') == '1',
            is_followers_only=parsed['tags'].get('followers-only') != '-1',
            is_unique_only=parsed['tags'].get('r9k') == '1',
            follower_only_delay=int(parsed['tags'].get('followers-only', '-1')),
            room_id=parsed['tags'].get('room-id'),
            slow=int(parsed['tags'].get('slow', '0')))
        prev = self.room_cache.get(state.name)
        # create copy
        if prev is not None:
            prev = dataclasses.replace(prev)
        self.room_cache[state.name] = state
        dat = RoomStateChangeEvent(self, prev, state)
        for handler in self._event_handler.get(ChatEvent.ROOM_STATE_CHANGE, []):
            t = asyncio.ensure_future(handler(dat), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)

    async def _handle_user_state(self, parsed: dict):
        self.logger.debug('got user state event')
        is_broadcaster = False
        if parsed['tags'].get('badges') is not None:
            is_broadcaster = parsed['tags']['badges'].get('broadcaster') is not None
        self._mod_status_cache[parsed['command']['channel'][1:]] = 'mod' if parsed['tags']['mod'] == '1' or is_broadcaster else 'user'
        self._subscriber_status_cache[parsed['command']['channel'][1:]] = 'sub' if parsed['tags']['subscriber'] == '1' else 'non-sub'

    async def _handle_ping(self, parsed: dict):
        self.logger.debug('got PING')
        await self._send_message('PONG ' + parsed['parameters'])

    # noinspection PyUnusedLocal
    async def _handle_ready(self, parsed: dict):
        self.logger.debug('got ready event')
        dat = EventData(self)
        was_ready = self._ready
        self._ready = True
        if self._join_target is not None and len(self._join_target) > 0:
            _failed = await self.join_room(self._join_target)
            if len(_failed) > 0:
                self.logger.warning(f'failed to join the following channel of the initial following list: {", ".join(_failed)}')
            else:
                self.logger.info('done joining initial channels')
        if not was_ready:
            for h in self._event_handler.get(ChatEvent.READY, []):
                t = asyncio.ensure_future(h(dat), loop=self._callback_loop)
                t.add_done_callback(self._task_callback)

    async def _handle_msg(self, parsed: dict):
        if self.no_shared_chat_messages and "source-room-id" in parsed["tags"]:
            if parsed["tags"]["source-room-id"] != parsed["tags"].get("room-id"):
                return

        async def _can_execute_command(_com: ChatCommand, _name: str) -> bool:
            for mid in self._command_middleware + self._command_specific_middleware.get(_name, []):
                if not await mid.can_execute(command):
                    if mid.execute_blocked_handler is not None:
                        await mid.execute_blocked_handler(_com)
                    elif self.default_command_execution_blocked_handler is not None:
                        await self.default_command_execution_blocked_handler(_com)
                    return False
            return True

        self.logger.debug('got new message, call handler')
        if parsed['command'].get('bot_command') is not None:
            command_name = parsed['command'].get('bot_command').lower()
            handler = self._command_handler.get(command_name)
            if handler is not None:
                command = ChatCommand(self, parsed)
                # check middleware
                if await _can_execute_command(command, command_name):
                    t = asyncio.ensure_future(handler(command), loop=self._callback_loop)
                    t.add_done_callback(self._task_callback)
                    for _mid in self._command_middleware + self._command_specific_middleware.get(command_name, []):
                        await _mid.was_executed(command)
            else:
                if self.log_no_registered_command_handler:
                    self.logger.info(f'no handler registered for command "{command_name}"')
        handler = self._event_handler.get(ChatEvent.MESSAGE, [])
        message = ChatMessage(self, parsed)
        for h in handler:
            t = asyncio.ensure_future(h(message), loop=self._callback_loop)
            t.add_done_callback(self._task_callback)

    async def __task_startup(self):
        await self._send_message('CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands')
        await self._send_message(f'PASS oauth:{await self.twitch.get_refreshed_user_auth_token()}')
        await self._send_message(f'NICK {self.username}')
        self.__startup_complete = True

    def _get_message_bucket(self, channel) -> RateLimitBucket:
        bucket = self._send_buckets.get(channel)
        if bucket is None:
            bucket = RateLimitBucket(30, 20, channel, self.logger)
            self._send_buckets[channel] = bucket
        target_size = RATE_LIMIT_SIZES[self._mod_status_cache.get(channel, 'user')]
        if bucket.bucket_size != target_size:
            bucket.bucket_size = target_size
        return bucket

    ##################################################################################################################################################
    # user functions
    ##################################################################################################################################################

    def set_prefix(self, prefix: str):
        """Sets a command prefix.

        The default prefix is !, the prefix can not start with / or .

        :param prefix: the new prefix to use for command parsing
        :raises ValueError: when the given prefix is None or starts with / or .
        """
        if prefix is None or prefix[0] in ('/', '.'):
            raise ValueError('Prefix starting with / or . are reserved for twitch internal use')
        self._prefix = prefix

    def set_channel_prefix(self, prefix: str, channel: Union[CHATROOM_TYPE, List[CHATROOM_TYPE]]):
        """Sets a command prefix for the given channel or channels

        The default channel prefix is either ! or the one set by :const:`~twitchAPI.chat.Chat.set_prefix()`, the prefix can not start with / or .

        :param prefix: the new prefix to use for commands in the given channels
        :param channel: the channel or channels you want the given command prefix to be used in
        :raises ValueError: when the given prefix is None or starts with / or .
        """
        if prefix is None or prefix[0] in ('/', '.'):
            raise ValueError('Prefix starting with / or . are reserved for twitch internal use')
        if not isinstance(channel, List):
            channel = [channel]
        for ch in channel:
            if isinstance(ch, ChatRoom):
                ch = ch.name
            self._channel_command_prefix[ch] = prefix

    def reset_channel_prefix(self, channel: Union[CHATROOM_TYPE, List[CHATROOM_TYPE]]):
        """Resets the custom command prefix set by :const:`~twitchAPI.chat.Chat.set_channel_prefix()` back to the global one.

        :param channel: The channel or channels you want to reset the channel command prefix for
        """
        if not isinstance(channel, List):
            channel = [channel]
        for ch in channel:
            if isinstance(ch, ChatRoom):
                ch = ch.name
            self._channel_command_prefix.pop(ch, None)

    def register_command(self, name: str, handler: COMMAND_CALLBACK_TYPE, command_middleware: Optional[List['BaseCommandMiddleware']] = None) -> bool:
        """Register a command

        :param name: the name of the command
        :param handler: The event handler
        :param command_middleware: a optional list of middleware to use just for this command
        :raises ValueError: if handler is not a coroutine"""
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError('handler needs to be a async function which takes one parameter')
        name = name.lower()
        if self._command_handler.get(name) is not None:
            return False
        self._command_handler[name] = handler
        if command_middleware is not None:
            self._command_specific_middleware[name] = command_middleware
        return True

    def unregister_command(self, name: str) -> bool:
        """Unregister a already registered command.

        :param name: the name of the command to unregister
        :return: True if the command was unregistered, otherwise false
        """
        name = name.lower()
        if self._command_handler.get(name) is None:
            return False
        self._command_handler.pop(name, None)
        return True

    def register_event(self, event: ChatEvent, handler: EVENT_CALLBACK_TYPE):
        """Register a event handler

        :param event: The Event you want to register the handler to
        :param handler: The handler you want to register.
        :raises ValueError: if handler is not a coroutine"""
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError('handler needs to be a async function which takes one parameter')
        if self._event_handler.get(event) is None:
            self._event_handler[event] = [handler]
        else:
            self._event_handler[event].append(handler)

    def unregister_event(self, event: ChatEvent, handler: EVENT_CALLBACK_TYPE) -> bool:
        """Unregister a handler from a event

        :param event: The Event you want to unregister your handler from
        :param handler: The handler you want to unregister
        :return: Returns true when the handler was removed from the event, otherwise false
        """
        if self._event_handler.get(event) is None or handler not in self._event_handler.get(event):
            return False
        self._event_handler[event].remove(handler)
        return True

    def is_connected(self) -> bool:
        """Returns your current connection status."""
        if self.__connection is None:
            return False
        return not self.__connection.closed

    def is_ready(self) -> bool:
        """Returns True if the chat bot is ready to join channels and/or receive events"""
        return self._ready

    def is_mod(self, room: CHATROOM_TYPE) -> bool:
        """Check if chat bot is a mod in a channel

        :param room: The chat room you want to check if bot is a mod in.
            This can either be a instance of :const:`~twitchAPI.type.ChatRoom` or a string with the room name (either with leading # or without)
        :return: Returns True if chat bot is a mod """
        if isinstance(room, ChatRoom):
            room = room.name
        if room is None or len(room) == 0:
            raise ValueError('please specify a room')
        if room[0] == '#':
            room = room[1:]
        return self._mod_status_cache.get(room.lower(), 'user') == 'mod'

    def is_subscriber(self, room: CHATROOM_TYPE) -> bool:
        """Check if chat bot is a subscriber in a channel

        :param room: The chat room you want to check if bot is a subscriber in.
            This can either be a instance of :const:`~twitchAPI.type.ChatRoom` or a string with the room name (either with leading # or without)
        :return: Returns True if chat bot is a subscriber """
        if isinstance(room, ChatRoom):
            room = room.name
        if room is None or len(room) == 0:
            raise ValueError('please specify a room')
        if room[0] == '#':
            room = room[1:]
        return self._subscriber_status_cache.get(room.lower(), 'user') == 'sub'

    def is_in_room(self, room: CHATROOM_TYPE) -> bool:
        """Check if the bot is currently in the given chat room

        :param room: The chat room you want to check
            This can either be a instance of :const:`~twitchAPI.type.ChatRoom` or a string with the room name (either with leading # or without)
        """
        if isinstance(room, ChatRoom):
            room = room.name
        if room is None or len(room) == 0:
            raise ValueError('please specify a room')
        if room[0] == '#':
            room = room[1:]
        return self.room_cache.get(room.lower()) is not None

    async def join_room(self, chat_rooms: Union[List[str], str]):
        """ join one or more chat rooms\n
        Will only exit once all given chat rooms where successfully joined or :const:`twitchAPI.chat.Chat.join_timeout` run out.

        :param chat_rooms: the Room or rooms you want to join
        :returns: list of channels that could not be joined
        """
        if isinstance(chat_rooms, str):
            chat_rooms = [chat_rooms]
        target = [c[1:].lower() if c[0] == '#' else c.lower() for c in chat_rooms]
        for r in target:
            self._room_join_locks.append(r)
        if len(target) > self._join_bucket.left():
            # we want to join more than the current bucket has left, join slowly one after another
            # TODO we could join the current remaining bucket size in blocks
            for r in target:
                await self._join_bucket.put()
                await self._send_message(f'JOIN #{r}')
        else:
            # enough space in the current bucket left, join all at once
            await self._join_bucket.put(len(target))
            await self._send_message(f'JOIN {",".join([f"#{x}" for x in target])}')
        # wait for us to join all rooms
        timeout = datetime.datetime.now() + datetime.timedelta(seconds=self.join_timeout)
        while any([r in self._room_join_locks for r in target]) and timeout > datetime.datetime.now():
            await asyncio.sleep(0.01)
        failed_to_join = [r for r in self._room_join_locks if r in target]
        self._join_target.extend([x for x in target if x not in failed_to_join])
        # deduplicate join target
        self._join_target = list(set(self._join_target))
        for r in failed_to_join:
            self._room_join_locks.remove(r)
        return failed_to_join

    async def send_raw_irc_message(self, message: str):
        """Send a raw IRC message

        :param message: the message to send
        :raises ValueError: if bot is not ready
        """
        if not self.is_ready():
            raise ValueError('can\'t send message: bot not ready')
        while not self.is_connected():
            await asyncio.sleep(0.1)
        if message is None or len(message) == 0:
            raise ValueError('message must be a non empty string')
        await self._send_message(message)

    async def send_message(self, room: CHATROOM_TYPE, text: str):
        """Send a message to the given channel

        Please note that you first need to join a channel before you can send a message to it.

        :param room: The chat room you want to send the message to.
            This can either be a instance of :const:`~twitchAPI.type.ChatRoom` or a string with the room name (either with leading # or without)
        :param text: The text you want to send
        :raises ValueError: if message is empty or room is not given
        :raises ValueError: if bot is not ready
        """
        if not self.is_ready():
            raise ValueError('can\'t send message: bot not ready')
        while not self.is_connected():
            await asyncio.sleep(0.1)
        if isinstance(room, ChatRoom):
            room = room.name
        if room is None or len(room) == 0:
            raise ValueError('please specify a room to post to')
        if text is None or len(text) == 0:
            raise ValueError('you can\'t send a empty message')
        if room[0] != '#':
            room = f'#{room}'.lower()
        bucket = self._get_message_bucket(room[1:])
        await bucket.put()
        await self._send_message(f'PRIVMSG {room} :{text}')

    async def leave_room(self, chat_rooms: Union[List[str], str]):
        """leave one or more chat rooms\n
        Will only exit once all given chat rooms where successfully left

        :param chat_rooms: The room or rooms you want to leave"""
        if isinstance(chat_rooms, str):
            chat_rooms = [chat_rooms]
        room_str = ','.join([f'#{c}'.lower() if c[0] != '#' else c.lower() for c in chat_rooms])
        target = [c[1:].lower() if c[0] == '#' else c.lower() for c in chat_rooms]
        for r in target:
            self._room_leave_locks.append(r)
        await self._send_message(f'PART {room_str}')
        for x in target:
            if x in self._join_target:
                self._join_target.remove(x)
        # wait to leave all rooms
        while any([r in self._room_leave_locks for r in target]):
            await asyncio.sleep(0.01)

    def register_command_middleware(self, mid: 'BaseCommandMiddleware'):
        """Adds the given command middleware as a general middleware"""
        if mid not in self._command_middleware:
            self._command_middleware.append(mid)

    def unregister_command_middleware(self, mid: 'BaseCommandMiddleware'):
        """Removes the given command middleware from the general list"""
        if mid in self._command_middleware:
            self._command_middleware.remove(mid)
