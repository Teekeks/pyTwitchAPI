#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>
"""
Type Definitions
----------------"""
from dataclasses import dataclass
from enum import Enum
from typing_extensions import TypedDict
from enum_tools.documentation import document_enum

__all__ = ['AnalyticsReportType', 'AuthScope', 'ModerationEventType', 'TimePeriod', 'SortMethod', 'HypeTrainContributionMethod',
           'VideoType', 'AuthType', 'StatusCode', 'PubSubResponseError', 'CustomRewardRedemptionStatus', 'SortOrder',
           'BlockSourceContext', 'BlockReason', 'EntitlementFulfillmentStatus', 'PollStatus', 'PredictionStatus', 'AutoModAction',
           'AutoModCheckEntry', 'DropsEntitlementFulfillmentStatus', 'ChatEvent', 'ChatRoom',
           'TwitchAPIException', 'InvalidRefreshTokenException', 'InvalidTokenException', 'NotFoundException', 'TwitchAuthorizationException',
           'UnauthorizedException', 'MissingScopeException', 'TwitchBackendException', 'PubSubListenTimeoutException', 'MissingAppSecretException',
           'EventSubSubscriptionTimeout', 'EventSubSubscriptionConflict', 'EventSubSubscriptionError', 'DeprecatedError', 'TwitchResourceNotFound',
           'ForbiddenError']


class AnalyticsReportType(Enum):
    """Enum of all Analytics report types
    """
    V1 = 'overview_v1'
    V2 = 'overview_v2'

@document_enum
class AuthScope(Enum):
    """Enum of Authentication scopes"""
    ANALYTICS_READ_EXTENSION = 'analytics:read:extensions'
    """View analytics data for the Twitch Extensions owned by the authenticated account.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_game_analytics()`
    """
    ANALYTICS_READ_GAMES = 'analytics:read:games'
    """View analytics data for the games owned by the authenticated account.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_game_analytics()`
    """
    BITS_READ = 'bits:read'
    """View Bits information for a channel.
             
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_bits_leaderboard()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_cheer()`
    """
    CHANNEL_READ_SUBSCRIPTIONS = 'channel:read:subscriptions'
    """View a list of all subscribers to a channel and check if a user is subscribed to a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_broadcaster_subscriptions()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscribe()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_end()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_gift()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_message()` |br|
    """
    CHANNEL_READ_STREAM_KEY = 'channel:read:stream_key'
    """View an authorized user’s stream key.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_stream_key()` |br|
    """
    CHANNEL_EDIT_COMMERCIAL = 'channel:edit:commercial'
    """Run commercials on a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.start_commercial()`
    """
    CHANNEL_READ_HYPE_TRAIN = 'channel:read:hype_train'
    """View Hype Train information for a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_hype_train_events()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_end()` |br|
    """
    CHANNEL_MANAGE_BROADCAST = 'channel:manage:broadcast'
    """Manage a channel’s broadcast configuration, including updating channel configuration and managing stream markers and stream tags.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.modify_channel_information()` |br|
    :const:`~twitchAPI.twitch.Twitch.create_stream_marker()`
    """
    CHANNEL_READ_REDEMPTIONS = 'channel:read:redemptions'
    """View Channel Points custom rewards and their redemptions on a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_custom_reward()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_custom_reward_redemption()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_automatic_reward_redemption_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_update()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_remove()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_update()` |br|
    """
    CHANNEL_MANAGE_REDEMPTIONS = 'channel:manage:redemptions'
    """Manage Channel Points custom rewards and their redemptions on a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_custom_reward()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_custom_reward_redemption()` |br|
    :const:`~twitchAPI.twitch.Twitch.create_custom_reward()` |br|
    :const:`~twitchAPI.twitch.Twitch.delete_custom_reward()` |br|
    :const:`~twitchAPI.twitch.Twitch.update_custom_reward()` |br|
    :const:`~twitchAPI.twitch.Twitch.update_redemption_status()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_automatic_reward_redemption_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_update()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_remove()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_update()` |br|
    """
    CHANNEL_READ_CHARITY = 'channel:read:charity'
    """Read charity campaign details and user donations on your channel.
           
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_charity_campaign()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_charity_donations()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_donate()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_start()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_stop()` |br|
    """
    CLIPS_EDIT = 'clips:edit'
    """Manage Clips for a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.create_clip()` |br|
    """
    USER_EDIT = 'user:edit'
    """Manage a user object.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_user()` |br|
    """
    USER_EDIT_BROADCAST = 'user:edit:broadcast'
    """View and edit a user’s broadcasting configuration, including Extension configurations.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_extensions()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_active_extensions()` |br|
    :const:`~twitchAPI.twitch.Twitch.update_user_extensions()` |br|
    """
    USER_READ_BROADCAST = 'user:read:broadcast'
    """View a user’s broadcasting configuration, including Extension configurations.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_stream_markers()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_extensions()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_active_extensions()` |br|
    """
    USER_READ_EMAIL = 'user:read:email'
    """View a user’s email address.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_users()` (optional) |br|
    :const:`~twitchAPI.twitch.Twitch.update_user()` (optional) |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_update()` (optional) |br|
    """
    USER_EDIT_FOLLOWS = 'user:edit:follows'
    CHANNEL_MODERATE = 'channel:moderate'
    CHAT_EDIT = 'chat:edit'
    """Send chat messages to a chatroom using an IRC connection."""
    CHAT_READ = 'chat:read'
    """View chat messages sent in a chatroom using an IRC connection."""
    WHISPERS_READ = 'whispers:read'
    """Receive whisper messages for your user using PubSub."""
    WHISPERS_EDIT = 'whispers:edit'
    MODERATION_READ = 'moderation:read'
    """
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.check_automod_status()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_banned_users()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_moderators()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderator_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderator_remove()` |br|
    """
    CHANNEL_SUBSCRIPTIONS = 'channel_subscriptions'
    CHANNEL_READ_EDITORS = 'channel:read:editors'
    """View a list of users with the editor role for a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_channel_editors()`
    """
    CHANNEL_MANAGE_VIDEOS = 'channel:manage:videos'
    """Manage a channel’s videos, including deleting videos.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.delete_videos()` |br|
    """
    USER_READ_BLOCKED_USERS = 'user:read:blocked_users'
    """View the block list of a user.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_block_list()` |br|
    """
    USER_MANAGE_BLOCKED_USERS = 'user:manage:blocked_users'
    """Manage the block list of a user.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.block_user()` |br|
    :const:`~twitchAPI.twitch.Twitch.unblock_user()` |br|
    """
    USER_READ_SUBSCRIPTIONS = 'user:read:subscriptions'
    """View if an authorized user is subscribed to specific channels.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.check_user_subscription()` |br|
    """
    USER_READ_FOLLOWS = 'user:read:follows'
    """View the list of channels a user follows.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_followed_channels()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_followed_streams()` |br|
    """
    CHANNEL_READ_GOALS = 'channel:read:goals'
    """View Creator Goals for a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_creator_goals()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_end()` |br|
    """
    CHANNEL_READ_POLLS = 'channel:read:polls'
    """View a channel’s polls.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_polls()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_end()` |br|
    """
    CHANNEL_MANAGE_POLLS = 'channel:manage:polls'
    """Manage a channel’s polls.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_polls()` |br|
    :const:`~twitchAPI.twitch.Twitch.create_poll()` |br|
    :const:`~twitchAPI.twitch.Twitch.end_poll()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_end()` |br|
    """
    CHANNEL_READ_PREDICTIONS = 'channel:read:predictions'
    """View a channel’s Channel Points Predictions.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_predictions()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_lock()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_end()` |br|
    """
    CHANNEL_MANAGE_PREDICTIONS = 'channel:manage:predictions'
    """Manage of channel’s Channel Points Predictions
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_predictions()` |br|
    :const:`~twitchAPI.twitch.Twitch.create_prediction()` |br|
    :const:`~twitchAPI.twitch.Twitch.end_prediction()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_progress()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_lock()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_end()` |br|
    """
    MODERATOR_MANAGE_AUTOMOD = 'moderator:manage:automod'
    """Manage messages held for review by AutoMod in channels where you are a moderator.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.manage_held_automod_message()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_message_hold()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_message_update()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_terms_update()` |br|
    """
    CHANNEL_MANAGE_SCHEDULE = 'channel:manage:schedule'
    """Manage a channel’s stream schedule.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_channel_stream_schedule()` |br|
    :const:`~twitchAPI.twitch.Twitch.create_channel_stream_schedule_segment()` |br|
    :const:`~twitchAPI.twitch.Twitch.update_channel_stream_schedule_segment()` |br|
    :const:`~twitchAPI.twitch.Twitch.delete_channel_stream_schedule_segment()` |br|
    """
    MODERATOR_MANAGE_CHAT_SETTINGS = 'moderator:manage:chat_settings'
    """Manage a broadcaster’s chat room settings.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_chat_settings()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_CHAT_SETTINGS = 'moderator:read:chat_settings'
    """View a broadcaster’s chat room settings.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_chat_settings()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|"""
    MODERATOR_MANAGE_BANNED_USERS = 'moderator:manage:banned_users'
    """Ban and unban users.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_banned_users()` |br|
    :const:`~twitchAPI.twitch.Twitch.ban_user()` |br|
    :const:`~twitchAPI.twitch.Twitch.unban_user()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_BANNED_USERS = 'moderator:read:banned_users'
    """Read banned users.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_BLOCKED_TERMS = 'moderator:read:blocked_terms'
    """View a broadcaster’s list of blocked terms.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_blocked_terms()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_MANAGE_BLOCKED_TERMS = 'moderator:manage:blocked_terms'
    """Manage a broadcaster’s list of blocked terms.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_blocked_terms()` |br|
    :const:`~twitchAPI.twitch.Twitch.add_blocked_term()` |br|
    :const:`~twitchAPI.twitch.Twitch.remove_blocked_term()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    CHANNEL_MANAGE_RAIDS = 'channel:manage:raids'
    """Manage a channel raiding another channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.start_raid()` |br|
    :const:`~twitchAPI.twitch.Twitch.cancel_raid()` |br|
    """
    MODERATOR_MANAGE_ANNOUNCEMENTS = 'moderator:manage:announcements'
    """Send announcements in channels where you have the moderator role.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_chat_announcement()` |br|
    """
    MODERATOR_MANAGE_CHAT_MESSAGES = 'moderator:manage:chat_messages'
    """Delete chat messages in channels where you have the moderator role.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.delete_chat_message()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_CHAT_MESSAGES = 'moderator:read:chat_messages'
    """Read deleted chat messages in channels where you have the moderator role.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_WARNINGS = 'moderator:read:warnings'
    """Read warnings in channels where you have the moderator role.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_acknowledge()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_send()` |br|
    """
    MODERATOR_MANAGE_WARNINGS = 'moderator:manage:warnings'
    """Warn users in channels where you have the moderator role.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.warn_chat_user()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_acknowledge()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_send()` |br|
    """
    USER_MANAGE_CHAT_COLOR = 'user:manage:chat_color'
    """Update the color used for the user’s name in chat.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_user_chat_color()` |br|
    """
    CHANNEL_MANAGE_MODERATORS = 'channel:manage:moderators'
    """Add or remove the moderator role from users in your channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.add_channel_moderator()` |br|
    :const:`~twitchAPI.twitch.Twitch.remove_channel_moderator()` |br|
    :const:`~twitchAPI.twitch.Twitch.get_moderators()` |br|
    """
    CHANNEL_READ_VIPS = 'channel:read:vips'
    """Read the list of VIPs in your channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_vips()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_remove()` |br|
    """
    MODERATOR_READ_MODERATORS = 'moderator:read:moderators'
    """Read the list of channels you are moderator in.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_VIPS = 'moderator:read:vips'
    CHANNEL_MANAGE_VIPS = 'channel:manage:vips'
    """Add or remove the VIP role from users in your channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_vips()` |br|
    :const:`~twitchAPI.twitch.Twitch.add_channel_vip()` |br|
    :const:`~twitchAPI.twitch.Twitch.remove_channel_vip()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_add()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_remove()` |br|
    """
    USER_READ_WHISPERS = 'user:read:whispers'
    """Receive whispers sent to your user.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_whisper_message()` |br|
    """
    USER_MANAGE_WHISPERS = 'user:manage:whispers'
    """Receive whispers sent to your user, and send whispers on your user’s behalf.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_whisper()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_whisper_message()` |br|
    """
    MODERATOR_READ_CHATTERS = 'moderator:read:chatters'
    """View the chatters in a broadcaster’s chat room.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_chatters()` |br|
    """
    MODERATOR_READ_SHIELD_MODE = 'moderator:read:shield_mode'
    """View a broadcaster’s Shield Mode status.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_shield_mode_status()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_end()` |br|
    """
    MODERATOR_MANAGE_SHIELD_MODE = 'moderator:manage:shield_mode'
    """Manage a broadcaster’s Shield Mode status.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_shield_mode_status()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_begin()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_end()` |br|
    """
    MODERATOR_READ_AUTOMOD_SETTINGS = 'moderator:read:automod_settings'
    """View a broadcaster’s AutoMod settings.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_automod_settings()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_settings_update()` |br|
    """
    MODERATOR_MANAGE_AUTOMOD_SETTINGS = 'moderator:manage:automod_settings'
    """Manage a broadcaster’s AutoMod settings.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.update_automod_settings()` |br|
    """
    MODERATOR_READ_FOLLOWERS = 'moderator:read:followers'
    """Read the followers of a broadcaster.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_channel_followers()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_follow_v2()` |br|
    """
    MODERATOR_MANAGE_SHOUTOUTS = 'moderator:manage:shoutouts'
    """Manage a broadcaster’s shoutouts.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_a_shoutout()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_create()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_receive()` |br|
    """
    MODERATOR_READ_SHOUTOUTS = 'moderator:read:shoutouts'
    """View a broadcaster’s shoutouts.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_create()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_receive()` |br|
    """
    CHANNEL_BOT = 'channel:bot'
    """Joins your channel’s chatroom as a bot user, and perform chat-related actions as that user.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_chat_message()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear_user_messages()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message_delete()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_notification()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_settings_update()` 
    """
    USER_BOT = 'user:bot'
    """Join a specified chat channel as your user and appear as a bot, and perform chat-related actions as your user.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_chat_message()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear_user_messages()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message_delete()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_notification()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_settings_update()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_hold()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_update()` |br|
    """
    USER_READ_CHAT = 'user:read:chat'
    """Receive chatroom messages and informational notifications relating to a channel’s chatroom.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear_user_messages()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message_delete()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_notification()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_settings_update()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_hold()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_update()` |br|
    """
    CHANNEL_READ_ADS = 'channel:read:ads'
    """Read the ads schedule and details on your channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_ad_schedule()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_ad_break_begin()`
    """
    CHANNEL_MANAGE_ADS = 'channel:manage:ads'
    """Manage ads schedule on a channel.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_ad_schedule()`
    """
    USER_WRITE_CHAT = 'user:write:chat'
    """Send chat messages to a chatroom.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.send_chat_message()` |br|
    """
    USER_READ_MODERATED_CHANNELS = 'user:read:moderated_channels'
    """Read the list of channels you have moderator privileges in.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_moderated_channels()` |br|
    """
    USER_READ_EMOTES = 'user:read:emotes'
    """View emotes available to a user.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_user_emotes()` |br|
    """
    MODERATOR_READ_UNBAN_REQUESTS = 'moderator:read:unban_requests'
    """View a broadcaster’s unban requests.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.get_unban_requests()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_create()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_resolve()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_MANAGE_UNBAN_REQUESTS = 'moderator:manage:unban_requests'
    """Manage a broadcaster’s unban requests.
    
    **API** |br|
    :const:`~twitchAPI.twitch.Twitch.resolve_unban_requests()` |br|
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_create()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_resolve()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
    """
    MODERATOR_READ_SUSPICIOUS_USERS = 'moderator:read:suspicious_users'
    """Read chat messages from suspicious users and see users flagged as suspicious in channels where you have the moderator role.
    
    **EventSub** |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_suspicious_user_message()` |br|
    :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_suspicious_user_update()` |br|
    """

class ModerationEventType(Enum):
    """Enum of moderation event types
    """
    BAN = 'moderation.user.ban'
    UNBAN = 'moderation.user.unban'
    UNKNOWN = ''


class TimePeriod(Enum):
    """Enum of valid Time periods
    """
    ALL = 'all'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class SortMethod(Enum):
    """Enum of valid sort methods
    """
    TIME = 'time'
    TRENDING = 'trending'
    VIEWS = 'views'


class HypeTrainContributionMethod(Enum):
    """Enum of valid Hype Train contribution types
    """

    BITS = 'BITS'
    SUBS = 'SUBS'
    OTHER = 'OTHER'
    UNKNOWN = ''


class VideoType(Enum):
    """Enum of valid video types
    """
    ALL = 'all'
    UPLOAD = 'upload'
    ARCHIVE = 'archive'
    HIGHLIGHT = 'highlight'
    UNKNOWN = ''


class AuthType(Enum):
    """Type of authentication required. Only internal use
    """
    NONE = 0
    USER = 1
    APP = 2
    EITHER = 3


class StatusCode(Enum):
    """Enum Code Status, see https://dev.twitch.tv/docs/api/reference#get-code-status for more documentation
    """
    SUCCESSFULLY_REDEEMED = 'SUCCESSFULLY_REDEEMED'
    ALREADY_CLAIMED = 'ALREADY_CLAIMED'
    EXPIRED = 'EXPIRED'
    USER_NOT_ELIGIBLE = 'USER_NOT_ELIGIBLE'
    NOT_FOUND = 'NOT_FOUND'
    INACTIVE = 'INACTIVE'
    UNUSED = 'UNUSED'
    INCORRECT_FORMAT = 'INCORRECT_FORMAT'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    UNKNOWN_VALUE = ''


class PubSubResponseError(Enum):
    """
    """
    BAD_MESSAGE = 'ERR_BADMESSAGE'
    BAD_AUTH = 'ERR_BADAUTH'
    SERVER = 'ERR_SERVER'
    BAD_TOPIC = 'ERR_BADTOPIC'
    NONE = ''
    UNKNOWN = 'unknown error'


class CustomRewardRedemptionStatus(Enum):
    """
    """
    UNFULFILLED = 'UNFULFILLED'
    FULFILLED = 'FULFILLED'
    CANCELED = 'CANCELED'


class SortOrder(Enum):
    """
    """
    OLDEST = 'OLDEST'
    NEWEST = 'NEWEST'


class BlockSourceContext(Enum):
    """
    """
    CHAT = 'chat'
    WHISPER = 'whisper'


class BlockReason(Enum):
    """
    """
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    OTHER = 'other'


class EntitlementFulfillmentStatus(Enum):
    """
    """
    CLAIMED = 'CLAIMED'
    FULFILLED = 'FULFILLED'


class PollStatus(Enum):
    """
    """
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    MODERATED = 'MODERATED'
    INVALID = 'INVALID'
    TERMINATED = 'TERMINATED'
    ARCHIVED = 'ARCHIVED'


class PredictionStatus(Enum):
    """
    """
    ACTIVE = 'ACTIVE'
    RESOLVED = 'RESOLVED'
    CANCELED = 'CANCELED'
    LOCKED = 'LOCKED'


class AutoModAction(Enum):
    """
    """
    ALLOW = 'ALLOW'
    DENY = 'DENY'


class DropsEntitlementFulfillmentStatus(Enum):
    """
    """
    CLAIMED = 'CLAIMED'
    FULFILLED = 'FULFILLED'


class AutoModCheckEntry(TypedDict):
    msg_id: str
    """Developer-generated identifier for mapping messages to results."""
    msg_text: str
    """Message text"""

# CHAT

@document_enum
class ChatEvent(Enum):
    """Represents the possible events to listen for using :const:`~twitchAPI.chat.Chat.register_event()`"""
    READY = 'ready'
    """Triggered when the bot is started up and ready"""
    MESSAGE = 'message'
    """Triggered when someone wrote a message in a chat channel"""
    SUB = 'sub'
    """Triggered when someone subscribed to a channel"""
    RAID = 'raid'
    """Triggered when a channel gets raided"""
    ROOM_STATE_CHANGE = 'room_state_change'
    """Triggered when a chat channel is changed (e.g. sub only mode was enabled)"""
    JOIN = 'join'
    """Triggered when someone other than the bot joins a chat channel"""
    JOINED = 'joined'
    """Triggered when the bot joins a chat channel"""
    LEFT = 'left'
    """Triggered when the bot leaves a chat channel"""
    USER_LEFT = 'user_left'
    """Triggered when a user leaves a chat channel"""
    MESSAGE_DELETE = 'message_delete'
    """Triggered when a message gets deleted from a channel"""
    CHAT_CLEARED = 'chat_cleared'
    """Triggered when a user was banned, timed out or all messaged from a user where deleted"""
    WHISPER = 'whisper'
    """Triggered when someone whispers to your bot. NOTE: You need the :const:`~twitchAPI.type.AuthScope.WHISPERS_READ` Auth Scope
    to get this Event."""
    NOTICE = 'notice'
    """Triggered on server notice"""


@dataclass
class ChatRoom:
    name: str
    is_emote_only: bool
    is_subs_only: bool
    is_followers_only: bool
    is_unique_only: bool
    follower_only_delay: int
    room_id: str
    slow: int


# EXCEPTIONS


class TwitchAPIException(Exception):
    """Base Twitch API Exception"""
    pass


class InvalidRefreshTokenException(TwitchAPIException):
    """used User Refresh Token is invalid"""
    pass


class InvalidTokenException(TwitchAPIException):
    """Used if a invalid token is set for the client"""
    pass


class NotFoundException(TwitchAPIException):
    """Resource was not found with the given parameter"""
    pass


class TwitchAuthorizationException(TwitchAPIException):
    """Exception in the Twitch Authorization"""
    pass


class UnauthorizedException(TwitchAuthorizationException):
    """Not authorized to use this"""
    pass


class MissingScopeException(TwitchAuthorizationException):
    """authorization is missing scope"""
    pass


class TwitchBackendException(TwitchAPIException):
    """when the Twitch API itself is down"""
    pass


class PubSubListenTimeoutException(TwitchAPIException):
    """when a PubSub listen command times out"""
    pass


class MissingAppSecretException(TwitchAPIException):
    """When the app secret is not set but app authorization is attempted"""
    pass


class EventSubSubscriptionTimeout(TwitchAPIException):
    """When the waiting for a confirmed EventSub subscription timed out"""
    pass


class EventSubSubscriptionConflict(TwitchAPIException):
    """When you try to subscribe to a EventSub subscription that already exists"""
    pass


class EventSubSubscriptionError(TwitchAPIException):
    """if the subscription request was invalid"""
    pass


class DeprecatedError(TwitchAPIException):
    """If something has been marked as deprecated by the Twitch API"""
    pass


class TwitchResourceNotFound(TwitchAPIException):
    """If a requested resource was not found"""
    pass


class ForbiddenError(TwitchAPIException):
    """If you are not allowed to do that"""
    pass
