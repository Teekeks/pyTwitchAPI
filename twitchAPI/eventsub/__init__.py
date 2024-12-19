#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
EventSub
--------

EventSub lets you listen for events that happen on Twitch.

All available EventSub clients runs in their own thread, calling the given callback function whenever an event happens.

Look at :ref:`eventsub-available-topics` to find the topics you are interested in.

Available Transports
====================

EventSub is available with different types of transports, used for different applications.

.. list-table::
   :header-rows: 1

   * - Transport Method
     - Use Case
     - Auth Type
   * - :doc:`twitchAPI.eventsub.webhook`
     - Server / Multi User
     - App Authentication
   * - :doc:`twitchAPI.eventsub.websocket`
     - Client / Single User
     - User Authentication


.. _eventsub-available-topics:

Available Topics and Callback Payloads
======================================

List of available EventSub Topics.

The Callback Payload is the type of the parameter passed to the callback function you specified in :const:`listen_`.

.. list-table::
   :header-rows: 1

   * - Topic
     - Subscription Function & Callback Payload
     - Description
   * - **Channel Update** v1
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelUpdateEvent`
     - A broadcaster updates their channel properties e.g., category, title, mature flag, broadcast, or language.
   * - **Channel Update** v2
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_update_v2()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelUpdateEvent`
     - A broadcaster updates their channel properties e.g., category, title, content classification labels, broadcast, or language.
   * - **Channel Follow** v2
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_follow_v2()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelFollowEvent`
     - A specified channel receives a follow.
   * - **Channel Subscribe**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscribe()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSubscribeEvent`
     - A notification when a specified channel receives a subscriber. This does not include resubscribes.
   * - **Channel Subscription End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSubscriptionEndEvent`
     - A notification when a subscription to the specified channel ends.
   * - **Channel Subscription Gift**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_gift()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSubscriptionGiftEvent`
     - A notification when a viewer gives a gift subscription to one or more users in the specified channel.
   * - **Channel Subscription Message**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_subscription_message()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSubscriptionMessageEvent`
     - A notification when a user sends a resubscription chat message in a specific channel.
   * - **Channel Cheer**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_cheer()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelCheerEvent`
     - A user cheers on the specified channel.
   * - **Channel Raid**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_raid()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelRaidEvent`
     - A broadcaster raids another broadcaster’s channel.
   * - **Channel Ban**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_ban()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelBanEvent`
     - A viewer is banned from the specified channel.
   * - **Channel Unban**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelUnbanEvent`
     - A viewer is unbanned from the specified channel.
   * - **Channel Moderator Add**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderator_add()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelModeratorAddEvent`
     - Moderator privileges were added to a user on a specified channel.
   * - **Channel Moderator Remove**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderator_remove()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelModeratorRemoveEvent`
     - Moderator privileges were removed from a user on a specified channel.
   * - **Channel Points Custom Reward Add**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_add()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsCustomRewardAddEvent`
     - A custom channel points reward has been created for the specified channel.
   * - **Channel Points Custom Reward Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsCustomRewardUpdateEvent`
     - A custom channel points reward has been updated for the specified channel.
   * - **Channel Points Custom Reward Remove**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_remove()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsCustomRewardRemoveEvent`
     - A custom channel points reward has been removed from the specified channel.
   * - **Channel Points Custom Reward Redemption Add**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_add()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsCustomRewardRedemptionAddEvent`
     - A viewer has redeemed a custom channel points reward on the specified channel.
   * - **Channel Points Custom Reward Redemption Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_custom_reward_redemption_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsCustomRewardRedemptionUpdateEvent`
     - A redemption of a channel points custom reward has been updated for the specified channel.
   * - **Channel Poll Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPollBeginEvent`
     - A poll started on a specified channel.
   * - **Channel Poll Progress**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_progress()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPollProgressEvent`
     - Users respond to a poll on a specified channel.
   * - **Channel Poll End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_poll_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPollEndEvent`
     - A poll ended on a specified channel.
   * - **Channel Prediction Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPredictionEvent`
     - A Prediction started on a specified channel.
   * - **Channel Prediction Progress**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_progress()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPredictionEvent`
     - Users participated in a Prediction on a specified channel.
   * - **Channel Prediction Lock**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_lock()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPredictionEvent`
     - A Prediction was locked on a specified channel.
   * - **Channel Prediction End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_prediction_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPredictionEndEvent`
     - A Prediction ended on a specified channel.
   * - **Drop Entitlement Grant**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_drop_entitlement_grant()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.DropEntitlementGrantEvent`
     - An entitlement for a Drop is granted to a user.
   * - **Extension Bits Transaction Create**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_extension_bits_transaction_create()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ExtensionBitsTransactionCreateEvent`
     - A Bits transaction occurred for a specified Twitch Extension.
   * - **Goal Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.GoalEvent`
     - A goal begins on the specified channel.
   * - **Goal Progress**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_progress()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.GoalEvent`
     - A goal makes progress on the specified channel.
   * - **Goal End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_goal_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.GoalEvent`
     - A goal ends on the specified channel.
   * - **Hype Train Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.HypeTrainEvent`
     - A Hype Train begins on the specified channel.
   * - **Hype Train Progress**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_progress()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.HypeTrainEvent`
     - A Hype Train makes progress on the specified channel.
   * - **Hype Train End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_hype_train_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.HypeTrainEvent`
     - A Hype Train ends on the specified channel.
   * - **Stream Online**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_stream_online()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.StreamOnlineEvent`
     - The specified broadcaster starts a stream.
   * - **Stream Offline**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_stream_offline()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.StreamOfflineEvent`
     - The specified broadcaster stops a stream.
   * - **User Authorization Grant**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_authorization_grant()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.UserAuthorizationGrantEvent`
     - A user’s authorization has been granted to your client id.
   * - **User Authorization Revoke**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_authorization_revoke()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.UserAuthorizationRevokeEvent`
     - A user’s authorization has been revoked for your client id.
   * - **User Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.UserUpdateEvent`
     - A user has updated their account.
   * - **Channel Shield Mode Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ShieldModeEvent`
     - Sends a notification when the broadcaster activates Shield Mode.
   * - **Channel Shield Mode End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shield_mode_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ShieldModeEvent`
     - Sends a notification when the broadcaster deactivates Shield Mode.
   * - **Channel Charity Campaign Start**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_start()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.CharityCampaignStartEvent`
     - Sends a notification when the broadcaster starts a charity campaign.
   * - **Channel Charity Campaign Progress**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_progress()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.CharityCampaignProgressEvent`
     - Sends notifications when progress is made towards the campaign’s goal or when the broadcaster changes the fundraising goal.
   * - **Channel Charity Campaign Stop**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_stop()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.CharityCampaignStopEvent`
     - Sends a notification when the broadcaster stops a charity campaign.
   * - **Channel Charity Campaign Donate**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_charity_campaign_donate()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.CharityDonationEvent`
     - Sends a notification when a user donates to the broadcaster’s charity campaign.
   * - **Channel Shoutout Create**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_create()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelShoutoutCreateEvent`
     - Sends a notification when the specified broadcaster sends a Shoutout.
   * - **Channel Shoutout Receive**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shoutout_receive()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelShoutoutReceiveEvent`
     - Sends a notification when the specified broadcaster receives a Shoutout.
   * - **Channel Chat Clear**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatClearEvent`
     - A moderator or bot has cleared all messages from the chat room.
   * - **Channel Chat Clear User Messages**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_clear_user_messages()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatClearUserMessagesEvent`
     - A moderator or bot has cleared all messages from a specific user.
   * - **Channel Chat Message Delete**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message_delete()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatMessageDeleteEvent`
     - A moderator has removed a specific message.
   * - **Channel Chat Notification**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_notification()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatNotificationEvent`
     - A notification for when an event that appears in chat has occurred.
   * - **Channel Chat Message**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_message()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatMessageEvent`
     - Any user sends a message to a specific chat room.
   * - **Channel Ad Break Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_ad_break_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelAdBreakBeginEvent`
     - A midroll commercial break has started running.
   * - **Channel Chat Settings Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_settings_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatSettingsUpdateEvent`
     - A notification for when a broadcaster’s chat settings are updated.
   * - **Whisper Received**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_user_whisper_message()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.UserWhisperMessageEvent`
     - A user receives a whisper.
   * - **Channel Points Automatic Reward Redemption**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_points_automatic_reward_redemption_add()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelPointsAutomaticRewardRedemptionAddEvent`
     - A viewer has redeemed an automatic channel points reward on the specified channel.
   * - **Channel VIP Add**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_add()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelVIPAddEvent`
     - A VIP is added to the channel.
   * - **Channel VIP Remove**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_vip_remove()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelVIPRemoveEvent`
     - A VIP is removed from the channel.
   * - **Channel Unban Request Create**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_create()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelUnbanRequestCreateEvent`
     - A user creates an unban request.
   * - **Channel Unban Request Resolve**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_unban_request_resolve()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelUnbanRequestResolveEvent`
     - An unban request has been resolved.
   * - **Channel Suspicious User Message**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_suspicious_user_message()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSuspiciousUserMessageEvent`
     - A chat message has been sent by a suspicious user.
   * - **Channel Suspicious User Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_suspicious_user_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSuspiciousUserUpdateEvent`
     - A suspicious user has been updated.
   * - **Channel Moderate** v2
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_moderate()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelModerateEvent`
     - A moderator performs a moderation action in a channel. Includes warnings.
   * - **Channel Warning Acknowledgement**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_acknowledge()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelWarningAcknowledgeEvent`
     - A user awknowledges a warning. Broadcasters and moderators can see the warning’s details.
   * - **Channel Warning Send**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_warning_send()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelWarningSendEvent`
     - A user is sent a warning. Broadcasters and moderators can see the warning’s details.
   * - **Automod Message Hold**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_message_hold()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.AutomodMessageHoldEvent`
     - A user is notified if a message is caught by automod for review.
   * - **Automod Message Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_message_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.AutomodMessageUpdateEvent`
     - A message in the automod queue had its status changed.
   * - **Automod Settings Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_settings_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.AutomodSettingsUpdateEvent`
     - A notification is sent when a broadcaster’s automod settings are updated.
   * - **Automod Terms Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_automod_terms_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.AutomodTermsUpdateEvent`
     - A notification is sent when a broadcaster’s automod terms are updated. Changes to private terms are not sent.
   * - **Channel Chat User Message Hold**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_hold()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatUserMessageHoldEvent`
     - A user is notified if their message is caught by automod.
   * - **Channel Chat User Message Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_chat_user_message_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelChatUserMessageUpdateEvent`
     - A user is notified if their message’s automod status is updated.
   * - **Channel Shared Chat Session Begin**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shared_chat_begin()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSharedChatBeginEvent`
     - A notification when a channel becomes active in an active shared chat session.
   * - **Channel Shared Chat Session Update**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shared_chat_update()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSharedChatUpdateEvent`
     - A notification when the active shared chat session the channel is in changes.
   * - **Channel Shared Chat Session End**
     - Function: :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_shared_chat_end()` |br|
       Payload: :const:`~twitchAPI.object.eventsub.ChannelSharedChatEndEvent`
     - A notification when a channel leaves a shared chat session or the session ends.
"""
