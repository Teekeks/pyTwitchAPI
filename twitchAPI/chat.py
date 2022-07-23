#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
import asyncio
import threading
from logging import getLogger, Logger
from pprint import pprint
from time import sleep
from typing import List, Optional, Union, Callable, Dict
import websockets
from twitchAPI import TwitchBackendException, Twitch, AuthType, AuthScope, ChatEvent
from twitchAPI.helper import TWITCH_CHAT_URL
from twitchAPI.types import ChatRoom


class ChatUser:

    def __init__(self, chat, parsed):
        self.chat: 'Chat' = chat
        self.name: str = parsed['source']['nick'] if parsed['source']['nick'] is not None else f':{chat.username}'


class ChatCommand:

    def __init__(self, chat, parsed):
        self.chat: 'Chat' = chat
        self._parsed = parsed
        self.name: str = parsed['command'].get('bot_command')
        self.parameter: str = parsed['command'].get('bot_command_params', '')
        self.text: str = parsed['parameters']

    @property
    def room(self) -> Optional[ChatRoom]:
        return self.chat.room_cache.get(self._parsed['command']['channel'])

    @property
    def user(self) -> ChatUser:
        return ChatUser(self.chat, self._parsed)


class ChatMessage:

    def __init__(self, chat, parsed):
        self.chat: 'Chat' = chat
        self._parsed = parsed
        self.text = parsed['parameters']
        pass

    @property
    def room(self) -> Optional[ChatRoom]:
        return self.chat.room_cache.get(self._parsed['command']['channel'])

    @property
    def user(self) -> ChatUser:
        return ChatUser(self.chat, self._parsed)


class Chat:

    ping_frequency: int = 120
    ping_jitter: int = 4
    listen_confirm_timeout: int = 30
    reconnect_delay_steps: List[int] = [0, 1, 2, 4, 8, 16, 32, 64, 128]

    __connection = None
    __socket_thread: threading.Thread = None
    __running: bool = False
    __socket_loop = None
    __topics: dict = {}
    __startup_complete: bool = False

    __tasks = None

    __waiting_for_pong: bool = False
    logger: Logger = None
    __nonce_waiting_confirm: dict = {}
    connection_url: str = TWITCH_CHAT_URL
    _event_handler = {}
    _command_handler = {}
    room_cache: Dict[str, ChatRoom] = {}

    def __init__(self, twitch: Twitch, connection_url: Optional[str] = None):
        self.logger = getLogger('twitchAPI.chat')
        self.twitch = twitch
        if not self.twitch.has_required_auth(AuthType.USER, [AuthScope.CHAT_READ]):
            raise ValueError('passed twitch instance is missing User Auth.')
        data = self.twitch.get_users()
        self.username: str = data['data'][0]['login'].lower()
        if connection_url is not None:
            self.connection_url = connection_url

    ##################################################################################################################################################
    # command parsing
    ##################################################################################################################################################

    def parse_irc_message(self, message: str):
        parsed_message = {
            'tags': None,
            'source': None,
            'command': None,
            'parameters': None
        }
        idx = 0
        raw_tags_component = None
        raw_source_component = None
        raw_command_component = None
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

        parsed_message['command'] = self.parse_irc_command(raw_command_component)

        if parsed_message['command'] is None:
            return None

        if raw_tags_component is not None:
            parsed_message['tags'] = self.parse_irc_tags(raw_tags_component)

        parsed_message['source'] = self.parse_irc_source(raw_source_component)
        parsed_message['parameters'] = raw_parameters_component
        if raw_parameters_component is not None and raw_parameters_component[0] == '!':
            parsed_message['command'] = self.parse_irc_parameters(raw_parameters_component, parsed_message['command'])

        return parsed_message

    def parse_irc_parameters(self, raw_parameters_component: str, command):
        idx = 0
        command_parts = raw_parameters_component[1::].strip()
        try:
            params_idx = command_parts.index(' ')
        except ValueError:
            command['bot_command'] = command_parts
            return command
        command['bot_command'] = command_parts[:params_idx]
        command['bot_command_params'] = command_parts[params_idx:].strip()
        return command

    def parse_irc_source(self, raw_source_component: str):
        if raw_source_component is None:
            return None
        source_parts = raw_source_component.split('!')
        return {
            'nick': source_parts[0] if len(source_parts) == 2 else None,
            'host': source_parts[1] if len(source_parts) == 2 else source_parts[0]
        }

    def parse_irc_tags(self, raw_tags_component: str):
        tags_to_ignore = ('client-nonce', 'flags')
        parsed_tags = {}

        tags = raw_tags_component.split(';')

        for tag in tags:
            parsed_tag = tag.split('=')
            tag_value = None if parsed_tag[1] == '' else parsed_tag[1]
            if parsed_tag[0] in ('badges', 'badge-info'):
                if tag_value is not None:
                    d = {}
                    badges = tag_value.split(',')
                    for pair in badges:
                        badge_parts = pair.split('/')
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

    def parse_irc_command(self, raw_command_component: str):
        command_parts = raw_command_component.split(' ')

        if command_parts[0] in ('JOIN', 'PART', 'NOTICE', 'CLEARCHAT', 'HOSTTARGET', 'PRIVMSG', 'USERSTATE', 'ROOMSTATE', '001'):
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
            # FIXME actually log error
            return None
        elif command_parts[0] in ('002', '003', '004', '353', '366', '372', '375', '376'):
            # FIXME maybe parse 353?
            return None
        else:
            # FIXME actually log error
            # unexpected command
            return None

        return parsed_command

    ##################################################################################################################################################
    # general web socket tools
    ##################################################################################################################################################

    def start(self) -> None:
        """
        Start the PubSub Client

        :raises RuntimeError: if already started
        """
        self.logger.debug('starting chat...')
        if self.__running:
            raise RuntimeError('already started')
        self.__startup_complete = False
        self.__socket_thread = threading.Thread(target=self.__run_socket)
        self.__running = True
        self.__socket_thread.start()
        while not self.__startup_complete:
            sleep(0.01)
        self.logger.debug('chat started up!')

    def stop(self) -> None:
        """
        Stop the PubSub Client

        :raises RuntimeError: if the client is not running
        """

        if not self.__running:
            raise RuntimeError('not running')
        self.logger.debug('stopping chat...')
        self.__startup_complete = False
        self.__running = False
        for task in self.__tasks:
            task.cancel()
        self.__socket_loop.call_soon_threadsafe(self.__socket_loop.stop)
        self.logger.debug('chat stopped!')
        self.__socket_thread.join()

    async def __connect(self, is_startup=False):
        self.logger.debug('connecting...')
        if self.__connection is not None and self.__connection.open:
            await self.__connection.close()
        retry = 0
        need_retry = True
        while need_retry and retry < len(self.reconnect_delay_steps):
            need_retry = False
            try:
                self.__connection = await websockets.connect(self.connection_url, loop=self.__socket_loop)
            except websockets.InvalidHandshake:
                self.logger.warning(f'connection attempt failed, retry in {self.reconnect_delay_steps[retry]}s...')
                await asyncio.sleep(self.reconnect_delay_steps[retry])
                retry += 1
                need_retry = True
        if retry >= len(self.reconnect_delay_steps):
            raise TwitchBackendException('can\'t connect')

    def __run_socket(self):
        self.__socket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__socket_loop)

        # startup
        self.__socket_loop.run_until_complete(self.__connect(is_startup=True))

        self.__tasks = [
            asyncio.ensure_future(self.__task_receive(), loop=self.__socket_loop),
            asyncio.ensure_future(self.__task_startup(), loop=self.__socket_loop)
        ]

        try:
            self.__socket_loop.run_forever()
        except asyncio.CancelledError:
            pass
        if self.__connection.open:
            self.__socket_loop.run_until_complete(self.__connection.close())

    async def __send_message(self, message: str):
        self.logger.debug(f'Sending message "{message}"')
        await self.__connection.send(message)

    async def __task_receive(self):
        async for message in self.__connection:
            messages = message.split('\r\n')
            for m in messages:
                if len(m) == 0:
                    continue
                parsed = self.parse_irc_message(m)
                # a message we don't know or don't care about
                if parsed is None:
                    continue
                handlers: Dict[str, Callable] = {
                    'PING': self._handle_ping,
                    'PRIVMSG': self._handle_msg,
                    '001': self._handle_ready,
                    'ROOMSTATE': self._handle_room_state
                }
                handler = handlers.get(parsed['command']['command'])
                # pprint(parsed)
                if handler is not None:
                    asyncio.ensure_future(handler(parsed))

    async def _handle_room_state(self, parsed: dict):
        state = ChatRoom(
            name=parsed['command']['channel'],
            is_emote_only=parsed['tags'].get('emote-only') == '1',
            is_subs_only=parsed['tags'].get('subs-only') == '1',
            is_followers_only=parsed['tags'].get('followers-only') != '-1',
            is_unique_only=parsed['tags'].get('r9k') == '1',
            follower_only_delay=int(parsed['tags'].get('followers-only', '-1')),
            room_id=parsed['tags'].get('room_id'),
            slow=int(parsed['tags'].get('slow', '0')))
        self.room_cache[state.name] = state

    async def _handle_ping(self, parsed: dict):
        self.logger.debug('got PING')
        await self.__send_message('PONG ' + parsed['parameters'])

    async def _handle_ready(self, parsed: dict):
        self.logger.debug('got ready event')
        handler = self._event_handler.get(ChatEvent.READY, [])
        for h in handler:
            asyncio.ensure_future(h())

    async def _handle_msg(self, parsed: dict):
        self.logger.debug('got new message, call handler')
        if parsed['command'].get('bot_command') is not None:
            command_name = parsed['command'].get('bot_command').lower()
            handler = self._command_handler.get(command_name)
            if handler is not None:
                asyncio.ensure_future(handler(ChatCommand(self, parsed)))
            else:
                self.logger.info(f'no handler registered for command "{command_name}"')
            return
        handler = self._event_handler.get(ChatEvent.MESSAGE, [])
        pprint(parsed)
        message = ChatMessage(self, parsed)
        for h in handler:
            asyncio.ensure_future(h(message))

    async def __task_startup(self):
        await self.__send_message('CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands')
        await self.__send_message(f'PASS oauth:{self.twitch.get_user_auth_token()}')
        await self.__send_message(f'NICK {self.username}')
        self.__startup_complete = True

    ##################################################################################################################################################
    # user functions
    ##################################################################################################################################################

    def register_command(self, name: str, handler: Callable) -> bool:
        name = name.lower()
        if self._command_handler.get(name) is not None:
            return False
        self._command_handler[name] = handler
        return True

    def register_event(self, event: ChatEvent, handler: Callable):
        if self._event_handler.get(event) is None:
            self._event_handler[event] = [handler]
        else:
            self._event_handler[event].append(handler)

    async def join_room(self, chat_rooms: Union[List[str], str]):
        """ join one or more chat rooms

        :param chat_rooms:
        :return:
        """
        if isinstance(chat_rooms, str):
            chat_rooms = [chat_rooms]
        chat_rooms = ','.join([f'#{c}' if c[0] != '#' else c for c in chat_rooms])
        await self.__send_message(f'JOIN {chat_rooms}')

    async def send_message(self, room: Union[str, ChatRoom], text: str):
        if isinstance(room, ChatRoom):
            room = room.name
        if room[0] != '#':
            room = f'#{room}'
        await self.__send_message(f'PRIVMSG {room} :{text}')

