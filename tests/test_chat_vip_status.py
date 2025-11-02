"""
Unit tests for VIP status detection in Chat class.

Tests the new is_vip() method and _handle_user_state() VIP caching logic.
VIP status is detected from IRC USERSTATE badges (not legacy tags).
"""

import pytest
from unittest.mock import Mock
from twitchAPI.chat import Chat
from twitchAPI.type import ChatRoom


class TestVIPStatusDetection:
    """Test VIP status detection and caching."""
    
    @pytest.fixture
    def chat_instance(self):
        """Create a Chat instance for testing (bypass async init)."""
        # Mock the Twitch instance
        mock_twitch = Mock()
        mock_twitch.has_required_auth = Mock(return_value=True)
        
        # Create Chat instance (calls __init__ directly)
        chat = Chat.__new__(Chat)
        chat.twitch = mock_twitch
        chat.username = "testbot"
        chat._mod_status_cache = {}
        chat._subscriber_status_cache = {}
        chat._vip_status_cache = {}
        chat.logger = Mock()
        
        return chat
    
    def test_vip_status_detected_from_badges(self, chat_instance):
        """Test that VIP status is correctly detected from badges dict."""
        parsed = {
            'tags': {
                'badges': {'vip': '1'},  # VIP badge present
                'mod': '0',
                'subscriber': '0',
                'vip': '0'  # Legacy tag (always 0, ignored)
            },
            'command': {'channel': '#testchannel'}
        }
        
        # Synchronously test (no await needed for internal method)
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        assert chat_instance.is_vip('testchannel') is True
        assert chat_instance.is_mod('testchannel') is False
    
    def test_non_vip_user(self, chat_instance):
        """Test that non-VIP users are correctly identified."""
        parsed = {
            'tags': {
                'badges': {},  # No badges
                'mod': '0',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        assert chat_instance.is_vip('testchannel') is False
    
    def test_broadcaster_is_not_vip(self, chat_instance):
        """Test that broadcaster is mod but NOT VIP."""
        parsed = {
            'tags': {
                'badges': {'broadcaster': '1'},  # Broadcaster badge
                'mod': '0',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        assert chat_instance.is_vip('testchannel') is False
        assert chat_instance.is_mod('testchannel') is True
    
    def test_moderator_is_not_vip(self, chat_instance):
        """Test that moderator is mod but NOT VIP."""
        parsed = {
            'tags': {
                'badges': {'moderator': '1'},  # Moderator badge
                'mod': '1',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        assert chat_instance.is_vip('testchannel') is False
        assert chat_instance.is_mod('testchannel') is True
    
    def test_vip_and_subscriber(self, chat_instance):
        """Test user who is both VIP and subscriber."""
        parsed = {
            'tags': {
                'badges': {'vip': '1', 'subscriber': '12'},
                'mod': '0',
                'subscriber': '1',
                'vip': '0'
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        assert chat_instance.is_vip('testchannel') is True
        assert chat_instance.is_subscriber('testchannel') is True
        assert chat_instance.is_mod('testchannel') is False
    
    def test_vip_cache_per_channel(self, chat_instance):
        """Test that VIP status is cached separately per channel."""
        # User is VIP in channel1
        parsed_vip = {
            'tags': {
                'badges': {'vip': '1'},
                'mod': '0',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#channel1'}
        }
        
        # User is NOT VIP in channel2
        parsed_non_vip = {
            'tags': {
                'badges': {},
                'mod': '0',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#channel2'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed_vip))
        asyncio.run(chat_instance._handle_user_state(parsed_non_vip))
        
        assert chat_instance.is_vip('channel1') is True
        assert chat_instance.is_vip('channel2') is False
    
    def test_is_vip_with_chatroom_object(self, chat_instance):
        """Test is_vip() accepts ChatRoom object as parameter."""
        parsed = {
            'tags': {
                'badges': {'vip': '1'},
                'mod': '0',
                'subscriber': '0',
                'vip': '0'
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        # Test with ChatRoom object
        room = ChatRoom(name='testchannel', is_emote_only=False, is_subs_only=False,
                       is_followers_only=False, is_unique_only=False,
                       follower_only_delay=-1, room_id='12345', slow=0)
        
        assert chat_instance.is_vip(room) is True
    
    def test_is_vip_raises_on_empty_room(self, chat_instance):
        """Test that is_vip() raises ValueError on empty room name."""
        with pytest.raises(ValueError, match='please specify a room'):
            chat_instance.is_vip('')
    
    def test_legacy_vip_tag_ignored(self, chat_instance):
        """Test that legacy vip='0' tag is ignored (only badges matter)."""
        # Even though vip='0' in tags, badges has VIP
        parsed = {
            'tags': {
                'badges': {'vip': '1'},
                'mod': '0',
                'subscriber': '0',
                'vip': '0'  # Legacy tag says NOT VIP (ignored)
            },
            'command': {'channel': '#testchannel'}
        }
        
        import asyncio
        asyncio.run(chat_instance._handle_user_state(parsed))
        
        # Should detect VIP from badges, not legacy tag
        assert chat_instance.is_vip('testchannel') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
