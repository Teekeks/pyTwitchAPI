#  Copyright (c) 2021. Lena "Teekeks" During <info@teawork.de>
"""
Base EventSub Client
--------------------

.. note:: This is the base class used for all EventSub Transport implementations.

  See :doc:`twitchAPI.eventsub` for a list of all available Transports.

*******************
Class Documentation
*******************
"""
from twitchAPI.object.eventsub import (ChannelPollBeginEvent, ChannelUpdateEvent, ChannelFollowEvent, ChannelSubscribeEvent,
                                       ChannelSubscriptionEndEvent, ChannelSubscriptionGiftEvent, ChannelSubscriptionMessageEvent,
                                       ChannelCheerEvent, ChannelRaidEvent, ChannelBanEvent, ChannelUnbanEvent,
                                       ChannelModeratorAddEvent, ChannelModeratorRemoveEvent, ChannelPointsCustomRewardAddEvent,
                                       ChannelPointsCustomRewardUpdateEvent, ChannelPointsCustomRewardRemoveEvent,
                                       ChannelPointsCustomRewardRedemptionAddEvent, ChannelPointsCustomRewardRedemptionUpdateEvent,
                                       ChannelPollProgressEvent, ChannelPollEndEvent, ChannelPredictionEvent, ChannelPredictionEndEvent,
                                       DropEntitlementGrantEvent, ExtensionBitsTransactionCreateEvent, GoalEvent, HypeTrainEvent, HypeTrainEndEvent,
                                       StreamOnlineEvent, StreamOfflineEvent, UserAuthorizationGrantEvent, UserAuthorizationRevokeEvent,
                                       UserUpdateEvent, ShieldModeEvent, CharityCampaignStartEvent, CharityCampaignProgressEvent,
                                       CharityCampaignStopEvent, CharityDonationEvent, ChannelShoutoutCreateEvent, ChannelShoutoutReceiveEvent,
                                       ChannelChatClearEvent, ChannelChatClearUserMessagesEvent, ChannelChatMessageDeleteEvent,
                                       ChannelChatNotificationEvent, ChannelAdBreakBeginEvent, ChannelChatMessageEvent, ChannelChatSettingsUpdateEvent,
                                       UserWhisperMessageEvent, ChannelPointsAutomaticRewardRedemptionAddEvent, ChannelVIPAddEvent,
                                       ChannelVIPRemoveEvent, ChannelUnbanRequestCreateEvent, ChannelUnbanRequestResolveEvent,
                                       ChannelSuspiciousUserMessageEvent, ChannelSuspiciousUserUpdateEvent, ChannelModerateEvent,
                                       ChannelWarningAcknowledgeEvent, ChannelWarningSendEvent, AutomodMessageHoldEvent, AutomodMessageUpdateEvent,
                                       AutomodSettingsUpdateEvent, AutomodTermsUpdateEvent, ChannelChatUserMessageHoldEvent, ChannelChatUserMessageUpdateEvent,
                                       ChannelSharedChatBeginEvent, ChannelSharedChatUpdateEvent, ChannelSharedChatEndEvent, ChannelBitsUseEvent,
                                       ChannelPointsAutomaticRewardRedemptionAdd2Event)
from twitchAPI.helper import remove_none_values
from twitchAPI.type import TwitchAPIException, AuthType
import asyncio
from logging import getLogger, Logger
from twitchAPI.twitch import Twitch
from abc import ABC, abstractmethod

from typing import Union, Callable, Optional, Awaitable

__all__ = ['EventSubBase']


class EventSubBase(ABC):
    """EventSub integration for the Twitch Helix API."""

    def __init__(self,
                 twitch: Twitch,
                 logger_name: str):
        """
        :param twitch: a app authenticated instance of :const:`~twitchAPI.twitch.Twitch`
        :param logger_name: the name of the logger to be used
        """
        self._twitch: Twitch = twitch
        self.logger: Logger = getLogger(logger_name)
        """The logger used for EventSub related log messages"""
        self._callbacks = {}

    @abstractmethod
    def start(self):
        """Starts the EventSub client

        :rtype: None
        :raises RuntimeError: if EventSub is already running
        """

    @abstractmethod
    async def stop(self):
        """Stops the EventSub client

        This also unsubscribes from all known subscriptions if unsubscribe_on_stop is True

        :rtype: None
        """

    @abstractmethod
    def _get_transport(self) -> dict:
        pass

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    @abstractmethod
    async def _build_request_header(self) -> dict:
        pass

    async def _api_post_request(self, session, url: str, data: Union[dict, None] = None):
        headers = await self._build_request_header()
        return await session.post(url, headers=headers, json=data)

    def _add_callback(self, c_id: str, callback, event):
        self._callbacks[c_id] = {'id': c_id, 'callback': callback, 'active': False, 'event': event}

    async def _activate_callback(self, c_id: str):
        if c_id not in self._callbacks:
            self.logger.debug(f'callback for {c_id} arrived before confirmation, waiting...')
        while c_id not in self._callbacks:
            await asyncio.sleep(0.1)
        self._callbacks[c_id]['active'] = True

    @abstractmethod
    async def _subscribe(self, sub_type: str, sub_version: str, condition: dict, callback, event, is_batching_enabled: Optional[bool] = None) -> str:
        pass

    # ==================================================================================================================
    # HANDLERS
    # ==================================================================================================================

    async def unsubscribe_all(self):
        """Unsubscribe from all subscriptions"""
        ret = await self._twitch.get_eventsub_subscriptions(target_token=self._target_token())
        async for d in ret:
            try:
                await self._twitch.delete_eventsub_subscription(d.id, target_token=self._target_token())
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {d.id}: {str(e)}')
        self._callbacks.clear()

    async def unsubscribe_all_known(self):
        """Unsubscribe from all subscriptions known to this client."""
        for key, value in self._callbacks.items():
            self.logger.debug(f'unsubscribe from event {key}')
            try:
                await self._twitch.delete_eventsub_subscription(key, target_token=self._target_token())
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {key}: {str(e)}')
        self._callbacks.clear()

    @abstractmethod
    def _target_token(self) -> AuthType:
        pass

    @abstractmethod
    async def _unsubscribe_hook(self, topic_id: str) -> bool:
        pass

    async def unsubscribe_topic(self, topic_id: str) -> bool:
        """Unsubscribe from a specific topic."""
        try:
            await self._twitch.delete_eventsub_subscription(topic_id, target_token=self._target_token())
            self._callbacks.pop(topic_id, None)
            return await self._unsubscribe_hook(topic_id)
        except TwitchAPIException as e:
            self.logger.warning(f'failed to unsubscribe from {topic_id}: {str(e)}')
        return False

    async def listen_channel_update(self, broadcaster_user_id: str, callback: Callable[[ChannelUpdateEvent], Awaitable[None]]) -> str:
        """A broadcaster updates their channel properties e.g., category, title, mature flag, broadcast, or language.

        No Authentication required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.update', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelUpdateEvent)

    async def listen_channel_update_v2(self, broadcaster_user_id: str, callback: Callable[[ChannelUpdateEvent], Awaitable[None]]) -> str:
        """A broadcaster updates their channel properties e.g., category, title, content classification labels or language.

        No Authentication required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.update', '2', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelUpdateEvent)

    async def listen_channel_follow_v2(self,
                                       broadcaster_user_id: str,
                                       moderator_user_id: str,
                                       callback: Callable[[ChannelFollowEvent], Awaitable[None]]) -> str:
        """A specified channel receives a follow.

        User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_FOLLOWERS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow

        :param broadcaster_user_id: the id of the user you want to listen to
        :param moderator_user_id: The ID of the moderator of the channel you want to get follow notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.follow',
                                     '2',
                                     {'broadcaster_user_id': broadcaster_user_id, 'moderator_user_id': moderator_user_id},
                                     callback,
                                     ChannelFollowEvent)

    async def listen_channel_subscribe(self, broadcaster_user_id: str, callback: Callable[[ChannelSubscribeEvent], Awaitable[None]]) -> str:
        """A notification when a specified channel receives a subscriber. This does not include resubscribes.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscribe

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.subscribe', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelSubscribeEvent)

    async def listen_channel_subscription_end(self,
                                              broadcaster_user_id: str,
                                              callback: Callable[[ChannelSubscriptionEndEvent], Awaitable[None]]) -> str:
        """A notification when a subscription to the specified channel ends.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.subscription.end', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelSubscriptionEndEvent)

    async def listen_channel_subscription_gift(self,
                                               broadcaster_user_id: str,
                                               callback: Callable[[ChannelSubscriptionGiftEvent], Awaitable[None]]) -> str:
        """A notification when a viewer gives a gift subscription to one or more users in the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptiongift

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.subscription.gift', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelSubscriptionGiftEvent)

    async def listen_channel_subscription_message(self,
                                                  broadcaster_user_id: str,
                                                  callback: Callable[[ChannelSubscriptionMessageEvent], Awaitable[None]]) -> str:
        """A notification when a user sends a resubscription chat message in a specific channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionmessage

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.subscription.message',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelSubscriptionMessageEvent)

    async def listen_channel_cheer(self, broadcaster_user_id: str, callback: Callable[[ChannelCheerEvent], Awaitable[None]]) -> str:
        """A user cheers on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.BITS_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelcheer

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.cheer',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelCheerEvent)

    async def listen_channel_raid(self,
                                  callback: Callable[[ChannelRaidEvent], Awaitable[None]],
                                  to_broadcaster_user_id: Optional[str] = None,
                                  from_broadcaster_user_id: Optional[str] = None) -> str:
        """A broadcaster raids another broadcaster’s channel.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelraid

        :param from_broadcaster_user_id: The broadcaster user ID that created the channel raid you want to get notifications for.
        :param to_broadcaster_user_id: The broadcaster user ID that received the channel raid you want to get notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.raid',
                                     '1',
                                     remove_none_values({
                                         'from_broadcaster_user_id': from_broadcaster_user_id,
                                         'to_broadcaster_user_id': to_broadcaster_user_id}),
                                     callback,
                                     ChannelRaidEvent)

    async def listen_channel_ban(self, broadcaster_user_id: str, callback: Callable[[ChannelBanEvent], Awaitable[None]]) -> str:
        """A viewer is banned from the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.ban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelBanEvent)

    async def listen_channel_unban(self, broadcaster_user_id: str, callback: Callable[[ChannelUnbanEvent], Awaitable[None]]) -> str:
        """A viewer is unbanned from the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelunban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.unban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelUnbanEvent)

    async def listen_channel_moderator_add(self, broadcaster_user_id: str, callback: Callable[[ChannelModeratorAddEvent], Awaitable[None]]) -> str:
        """Moderator privileges were added to a user on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatoradd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.moderator.add',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelModeratorAddEvent)

    async def listen_channel_moderator_remove(self,
                                              broadcaster_user_id: str,
                                              callback: Callable[[ChannelModeratorRemoveEvent], Awaitable[None]]) -> str:
        """Moderator privileges were removed from a user on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatorremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.moderator.remove',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelModeratorRemoveEvent)

    async def listen_channel_points_custom_reward_add(self,
                                                      broadcaster_user_id: str,
                                                      callback: Callable[[ChannelPointsCustomRewardAddEvent], Awaitable[None]]) -> str:
        """A custom channel points reward has been created for the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.channel_points_custom_reward.add',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelPointsCustomRewardAddEvent)

    async def listen_channel_points_custom_reward_update(self,
                                                         broadcaster_user_id: str,
                                                         callback: Callable[[ChannelPointsCustomRewardUpdateEvent], Awaitable[None]],
                                                         reward_id: Optional[str] = None) -> str:
        """A custom channel points reward has been updated for the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.channel_points_custom_reward.update',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback,
                                     ChannelPointsCustomRewardUpdateEvent)

    async def listen_channel_points_custom_reward_remove(self,
                                                         broadcaster_user_id: str,
                                                         callback: Callable[[ChannelPointsCustomRewardRemoveEvent], Awaitable[None]],
                                                         reward_id: Optional[str] = None) -> str:
        """A custom channel points reward has been removed from the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.channel_points_custom_reward.remove',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback,
                                     ChannelPointsCustomRewardRemoveEvent)

    async def listen_channel_points_custom_reward_redemption_add(self,
                                                                 broadcaster_user_id: str,
                                                                 callback: Callable[[ChannelPointsCustomRewardRedemptionAddEvent], Awaitable[None]],
                                                                 reward_id: Optional[str] = None) -> str:
        """A viewer has redeemed a custom channel points reward on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.channel_points_custom_reward_redemption.add',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback,
                                     ChannelPointsCustomRewardRedemptionAddEvent)

    async def listen_channel_points_custom_reward_redemption_update(self,
                                                                    broadcaster_user_id: str,
                                                                    callback: Callable[[ChannelPointsCustomRewardRedemptionUpdateEvent], Awaitable[None]],
                                                                    reward_id: Optional[str] = None) -> str:
        """A redemption of a channel points custom reward has been updated for the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.channel_points_custom_reward_redemption.update',
                                     '1',
                                     remove_none_values({
                                         'broadcaster_user_id': broadcaster_user_id,
                                         'reward_id': reward_id}),
                                     callback,
                                     ChannelPointsCustomRewardRedemptionUpdateEvent)

    async def listen_channel_poll_begin(self, broadcaster_user_id: str, callback: Callable[[ChannelPollBeginEvent], Awaitable[None]]) -> str:
        """A poll started on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.poll.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollBeginEvent)

    async def listen_channel_poll_progress(self, broadcaster_user_id: str, callback: Callable[[ChannelPollProgressEvent], Awaitable[None]]) -> str:
        """Users respond to a poll on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.poll.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollProgressEvent)

    async def listen_channel_poll_end(self, broadcaster_user_id: str, callback: Callable[[ChannelPollEndEvent], Awaitable[None]]) -> str:
        """A poll ended on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.poll.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollEndEvent)

    async def listen_channel_prediction_begin(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """A Prediction started on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.prediction.begin', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_progress(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """Users participated in a Prediction on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.prediction.progress', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_lock(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """A Prediction was locked on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionlock

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.prediction.lock', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_end(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEndEvent], Awaitable[None]]) -> str:
        """A Prediction ended on a specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.prediction.end', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEndEvent)

    async def listen_drop_entitlement_grant(self,
                                            organisation_id: str,
                                            callback: Callable[[DropEntitlementGrantEvent], Awaitable[None]],
                                            category_id: Optional[str] = None,
                                            campaign_id: Optional[str] = None) -> str:
        """An entitlement for a Drop is granted to a user.

        App access token required. The client ID associated with the access token must be owned by a user who is part of the specified organization.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#dropentitlementgrant

        :param organisation_id: The organization ID of the organization that owns the game on the developer portal.
        :param category_id: The category (or game) ID of the game for which entitlement notifications will be received. |default| :code:`None`
        :param campaign_id: The campaign ID for a specific campaign for which entitlement notifications will be received. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('drop.entitlement.grant',
                                     '1',
                                     remove_none_values({
                                         'organization_id': organisation_id,
                                         'category_id': category_id,
                                         'campaign_id': campaign_id
                                     }),
                                     callback, DropEntitlementGrantEvent, is_batching_enabled=True)

    async def listen_extension_bits_transaction_create(self,
                                                       extension_client_id: str,
                                                       callback: Callable[[ExtensionBitsTransactionCreateEvent], Awaitable[None]]) -> str:
        """A Bits transaction occurred for a specified Twitch Extension.

        The OAuth token client ID must match the Extension client ID.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#extensionbits_transactioncreate

        :param extension_client_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('extension.bits_transaction.create', '1', {'extension_client_id': extension_client_id}, callback,
                                     ExtensionBitsTransactionCreateEvent)

    async def listen_goal_begin(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal begins on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.goal.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_goal_progress(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.goal.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_goal_end(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal ends on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.goal.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_hype_train_begin(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEvent], Awaitable[None]]) -> str:
        """A Hype Train begins on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.hype_train.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEvent)

    async def listen_hype_train_progress(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEvent], Awaitable[None]]) -> str:
        """A Hype Train makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.hype_train.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEvent)

    async def listen_hype_train_end(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEndEvent], Awaitable[None]]) -> str:
        """A Hype Train ends on the specified channel.

        User Authentication with :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.hype_train.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEndEvent)

    async def listen_stream_online(self, broadcaster_user_id: str, callback: Callable[[StreamOnlineEvent], Awaitable[None]]) -> str:
        """The specified broadcaster starts a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamonline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('stream.online', '1', {'broadcaster_user_id': broadcaster_user_id}, callback, StreamOnlineEvent)

    async def listen_stream_offline(self, broadcaster_user_id: str, callback: Callable[[StreamOfflineEvent], Awaitable[None]]) -> str:
        """The specified broadcaster stops a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamoffline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('stream.offline', '1', {'broadcaster_user_id': broadcaster_user_id}, callback, StreamOfflineEvent)

    async def listen_user_authorization_grant(self, client_id: str, callback: Callable[[UserAuthorizationGrantEvent], Awaitable[None]]) -> str:
        """A user’s authorization has been granted to your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationgrant

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('user.authorization.grant', '1', {'client_id': client_id}, callback,
                                     UserAuthorizationGrantEvent)

    async def listen_user_authorization_revoke(self, client_id: str, callback: Callable[[UserAuthorizationRevokeEvent], Awaitable[None]]) -> str:
        """A user’s authorization has been revoked for your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationrevoke

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('user.authorization.revoke', '1', {'client_id': client_id}, callback,
                                     UserAuthorizationRevokeEvent)

    async def listen_user_update(self, user_id: str, callback: Callable[[UserUpdateEvent], Awaitable[None]]) -> str:
        """A user has updated their account.

        No authorization required. If you have the :const:`~twitchAPI.type.AuthScope.USER_READ_EMAIL` scope,
        the notification will include email field.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userupdate

        :param user_id: The user ID for the user you want update notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('user.update', '1', {'user_id': user_id}, callback, UserUpdateEvent)

    async def listen_channel_shield_mode_begin(self,
                                               broadcaster_user_id: str,
                                               moderator_user_id: str,
                                               callback: Callable[[ShieldModeEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster activates Shield Mode.

        Requires the :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modebegin

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they activate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shield_mode.begin', '1', param, callback, ShieldModeEvent)

    async def listen_channel_shield_mode_end(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: Callable[[ShieldModeEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster deactivates Shield Mode.

        Requires the :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modeend

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they deactivate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shield_mode.end', '1', param, callback, ShieldModeEvent)

    async def listen_channel_charity_campaign_start(self,
                                                    broadcaster_user_id: str,
                                                    callback: Callable[[CharityCampaignStartEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster starts a charity campaign.

        Requires the :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstart

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they start a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.start', '1', param, callback, CharityCampaignStartEvent)

    async def listen_channel_charity_campaign_progress(self,
                                                       broadcaster_user_id: str,
                                                       callback: Callable[[CharityCampaignProgressEvent], Awaitable[None]]) -> str:
        """Sends notifications when progress is made towards the campaign’s goal or when the broadcaster changes the fundraising goal.

        Requires the :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignprogress

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when their campaign makes progress or is updated.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.progress', '1', param, callback, CharityCampaignProgressEvent)

    async def listen_channel_charity_campaign_stop(self,
                                                   broadcaster_user_id: str,
                                                   callback: Callable[[CharityCampaignStopEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster stops a charity campaign.

        Requires the :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstop

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they stop a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.stop', '1', param, callback, CharityCampaignStopEvent)

    async def listen_channel_charity_campaign_donate(self,
                                                     broadcaster_user_id: str,
                                                     callback: Callable[[CharityDonationEvent], Awaitable[None]]) -> str:
        """Sends a notification when a user donates to the broadcaster’s charity campaign.

        Requires the :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaigndonate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when users donate to their campaign.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.donate', '1', param, callback, CharityDonationEvent)

    async def listen_channel_shoutout_create(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: Callable[[ChannelShoutoutCreateEvent], Awaitable[None]]) -> str:
        """Sends a notification when the specified broadcaster sends a Shoutout.

        Requires the :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutcreate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they send a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that gave the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shoutout.create', '1', param, callback, ChannelShoutoutCreateEvent)

    async def listen_channel_shoutout_receive(self,
                                              broadcaster_user_id: str,
                                              moderator_user_id: str,
                                              callback: Callable[[ChannelShoutoutReceiveEvent], Awaitable[None]]) -> str:
        """Sends a notification when the specified broadcaster receives a Shoutout.

        Requires the :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutreceive

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they receive a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that received the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shoutout.receive', '1', param, callback, ChannelShoutoutReceiveEvent)

    async def listen_channel_chat_clear(self,
                                        broadcaster_user_id: str,
                                        user_id: str,
                                        callback: Callable[[ChannelChatClearEvent], Awaitable[None]]) -> str:
        """A moderator or bot has cleared all messages from the chat room.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user. If app access token used, then additionally requires
        :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from
        broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatclear

        :param broadcaster_user_id: User ID of the channel to receive chat clear events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.clear', '1', param, callback, ChannelChatClearEvent)

    async def listen_channel_chat_clear_user_messages(self,
                                                      broadcaster_user_id: str,
                                                      user_id: str,
                                                      callback: Callable[[ChannelChatClearUserMessagesEvent], Awaitable[None]]) -> str:
        """A moderator or bot has cleared all messages from a specific user.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user. If app access token used, then additionally requires
        :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from
        broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatclear_user_messages

        :param broadcaster_user_id: User ID of the channel to receive chat clear user messages events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.clear_user_messages', '1', param, callback, ChannelChatClearUserMessagesEvent)

    async def listen_channel_chat_message_delete(self,
                                                 broadcaster_user_id: str,
                                                 user_id: str,
                                                 callback: Callable[[ChannelChatMessageDeleteEvent], Awaitable[None]]) -> str:
        """A moderator has removed a specific message.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user. If app access token used, then additionally requires
        :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from
        broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatmessage_delete

        :param broadcaster_user_id: User ID of the channel to receive chat message delete events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.message_delete', '1', param, callback, ChannelChatMessageDeleteEvent)

    async def listen_channel_chat_notification(self,
                                               broadcaster_user_id: str,
                                               user_id: str,
                                               callback: Callable[[ChannelChatNotificationEvent], Awaitable[None]]) -> str:
        """A notification for when an event that appears in chat has occurred.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user. If app access token used, then additionally requires
        :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from
        broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatnotification

        :param broadcaster_user_id: User ID of the channel to receive chat notification events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.notification', '1', param, callback, ChannelChatNotificationEvent)

    async def listen_channel_ad_break_begin(self,
                                            broadcaster_user_id: str,
                                            callback: Callable[[ChannelAdBreakBeginEvent], Awaitable[None]]) -> str:
        """A midroll commercial break has started running.

        Requires the :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_ADS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelad_breakbegin

        :param broadcaster_user_id: The ID of the broadcaster that you want to get Channel Ad Break begin notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        return await self._subscribe('channel.ad_break.begin', '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelAdBreakBeginEvent)

    async def listen_channel_chat_message(self,
                                          broadcaster_user_id: str,
                                          user_id: str,
                                          callback: Callable[[ChannelChatMessageEvent], Awaitable[None]]) -> str:
        """Any user sends a message to a specific chat room.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user.
        If app access token used, then additionally requires :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either
        :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatmessage

        :param broadcaster_user_id: User ID of the channel to receive chat message events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.message', '1', param, callback, ChannelChatMessageEvent)

    async def listen_channel_chat_settings_update(self,
                                                  broadcaster_user_id: str,
                                                  user_id: str,
                                                  callback: Callable[[ChannelChatSettingsUpdateEvent], Awaitable[None]]) -> str:
        """This event sends a notification when a broadcaster’s chat settings are updated.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from chatting user.
        If app access token used, then additionally requires :const:`~twitchAPI.type.AuthScope.USER_BOT` scope from chatting user, and either
        :const:`~twitchAPI.type.AuthScope.CHANNEL_BOT` scope from broadcaster or moderator status.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchat_settingsupdate

        :param broadcaster_user_id: User ID of the channel to receive chat settings update events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat_settings.update', '1', param, callback, ChannelChatSettingsUpdateEvent)

    async def listen_user_whisper_message(self,
                                          user_id: str,
                                          callback: Callable[[UserWhisperMessageEvent], Awaitable[None]]) -> str:
        """ Sends a notification when a user receives a whisper. Event Triggers - Anyone whispers the specified user.

        Requires :const:`~twitchAPI.type.AuthScope.USER_READ_WHISPERS` or :const:`~twitchAPI.type.AuthScope.USER_MANAGE_WHISPERS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#userwhispermessage

        :param user_id: The user_id of the person receiving whispers.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'user_id': user_id}
        return await self._subscribe('user.whisper.message', '1', param, callback, UserWhisperMessageEvent)

    async def listen_channel_points_automatic_reward_redemption_add(self,
                                                                    broadcaster_user_id: str,
                                                                    callback: Callable[[ChannelPointsAutomaticRewardRedemptionAddEvent], Awaitable[None]]) -> str:
        """A viewer has redeemed an automatic channel points reward on the specified channel.

        Requires :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchannel_points_automatic_reward_redemptionadd

        :param broadcaster_user_id: The broadcaster user ID for the channel you want to receive channel points reward add notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.channel_points_automatic_reward_redemption.add', '1', param, callback,
                                     ChannelPointsAutomaticRewardRedemptionAddEvent)

    async def listen_channel_points_automatic_reward_redemption_add_v2(self,
                                                                       broadcaster_user_id: str,
                                                                       callback: Callable[[ChannelPointsAutomaticRewardRedemptionAdd2Event], Awaitable[None]]) -> str:
        """A viewer has redeemed an automatic channel points reward on the specified channel.

        Requires :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_REDEMPTIONS` or :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchannel_points_automatic_reward_redemptionadd-v2

        :param broadcaster_user_id: The broadcaster user ID for the channel you want to receive channel points reward add notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.channel_points_automatic_reward_redemption.add', '2', param, callback,
                                     ChannelPointsAutomaticRewardRedemptionAdd2Event)

    async def listen_channel_vip_add(self,
                                     broadcaster_user_id: str,
                                     callback: Callable[[ChannelVIPAddEvent], Awaitable[None]]) -> str:
        """A VIP is added to the channel.

        Requires :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_VIPS` or :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_VIPS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelvipadd

        :param broadcaster_user_id: The User ID of the broadcaster
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.vip.add', '1', param, callback, ChannelVIPAddEvent)

    async def listen_channel_vip_remove(self,
                                        broadcaster_user_id: str,
                                        callback: Callable[[ChannelVIPRemoveEvent], Awaitable[None]]) -> str:
        """A VIP is removed from the channel.

        Requires :const:`~twitchAPI.type.AuthScope.CHANNEL_READ_VIPS` or :const:`~twitchAPI.type.AuthScope.CHANNEL_MANAGE_VIPS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelvipremove

        :param broadcaster_user_id: The User ID of the broadcaster
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.vip.remove', '1', param, callback, ChannelVIPRemoveEvent)

    async def listen_channel_unban_request_create(self,
                                                  broadcaster_user_id: str,
                                                  moderator_user_id: str,
                                                  callback: Callable[[ChannelUnbanRequestCreateEvent], Awaitable[None]]) -> str:
        """A user creates an unban request.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_UNBAN_REQUESTS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS` scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelunban_requestcreate

        :param broadcaster_user_id: The ID of the broadcaster you want to get chat unban request notifications for.
        :param moderator_user_id: The ID of the user that has permission to moderate the broadcaster’s channel and has granted your app permission to subscribe to this subscription type.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id,
                 'moderator_user_id': moderator_user_id}
        return await self._subscribe('channel.unban_request.create', '1', param, callback, ChannelUnbanRequestCreateEvent)

    async def listen_channel_unban_request_resolve(self,
                                                   broadcaster_user_id: str,
                                                   moderator_user_id: str,
                                                   callback: Callable[[ChannelUnbanRequestResolveEvent], Awaitable[None]]) -> str:
        """An unban request has been resolved.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_UNBAN_REQUESTS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelunban_requestresolve

        :param broadcaster_user_id: The ID of the broadcaster you want to get unban request resolution notifications for.
        :param moderator_user_id: The ID of the user that has permission to moderate the broadcaster’s channel and has granted your app permission to subscribe to this subscription type.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id,
                 'moderator_user_id': moderator_user_id}
        return await self._subscribe('channel.unban_request.resolve', '1', param, callback, ChannelUnbanRequestResolveEvent)

    async def listen_channel_suspicious_user_message(self,
                                                     broadcaster_user_id: str,
                                                     moderator_user_id: str,
                                                     callback: Callable[[ChannelSuspiciousUserMessageEvent], Awaitable[None]]) -> str:
        """A chat message has been sent by a suspicious user.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SUSPICIOUS_USERS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelsuspicious_usermessage

        :param broadcaster_user_id: User ID of the channel to receive chat message events for.
        :param moderator_user_id: The ID of a user that has permission to moderate the broadcaster’s channel and has granted your app permission
            to subscribe to this subscription type.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id,
                 'moderator_user_id': moderator_user_id}
        return await self._subscribe('channel.suspicious_user.message', '1', param, callback, ChannelSuspiciousUserMessageEvent)

    async def listen_channel_suspicious_user_update(self,
                                                    broadcaster_user_id: str,
                                                    moderator_user_id: str,
                                                    callback: Callable[[ChannelSuspiciousUserUpdateEvent], Awaitable[None]]) -> str:
        """A suspicious user has been updated.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_SUSPICIOUS_USERS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelsuspicious_userupdate

        :param broadcaster_user_id: The broadcaster you want to get chat unban request notifications for.
        :param moderator_user_id: The ID of a user that has permission to moderate the broadcaster’s channel and has granted your app permission
            to subscribe to this subscription type.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {'broadcaster_user_id': broadcaster_user_id,
                 'moderator_user_id': moderator_user_id}
        return await self._subscribe('channel.suspicious_user.update', '1', param, callback, ChannelSuspiciousUserUpdateEvent)

    async def listen_channel_moderate(self,
                                      broadcaster_user_id: str,
                                      moderator_user_id: str,
                                      callback: Callable[[ChannelModerateEvent], Awaitable[None]]) -> str:
        """A moderator performs a moderation action in a channel. Includes warnings.

        Requires all of the following scopes:

        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_BLOCKED_TERMS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_CHAT_SETTINGS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_UNBAN_REQUESTS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_BANNED_USERS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_BANNED_USERS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_CHAT_MESSAGES` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_WARNINGS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_WARNINGS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_MODERATORS`
        - :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_VIPS`

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelmoderate-v2

        :param broadcaster_user_id: The user ID of the broadcaster.
        :param moderator_user_id: The user ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.moderate', '2', param, callback, ChannelModerateEvent)

    async def listen_channel_warning_acknowledge(self,
                                                 broadcaster_user_id: str,
                                                 moderator_user_id: str,
                                                 callback: Callable[[ChannelWarningAcknowledgeEvent], Awaitable[None]]) -> str:
        """Sends a notification when a warning is acknowledged by a user.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_WARNINGS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_WARNINGS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelwarningacknowledge

        :param broadcaster_user_id: The User ID of the broadcaster.
        :param moderator_user_id: The User ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.warning.acknowledge', '1', param, callback, ChannelWarningAcknowledgeEvent)

    async def listen_channel_warning_send(self,
                                          broadcaster_user_id: str,
                                          moderator_user_id: str,
                                          callback: Callable[[ChannelWarningSendEvent], Awaitable[None]]) -> str:
        """Sends a notification when a warning is send to a user. Broadcasters and moderators can see the warning’s details.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_WARNINGS` or :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_WARNINGS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelwarningsend

        :param broadcaster_user_id: The User ID of the broadcaster.
        :param moderator_user_id: The User ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.warning.send', '1', param, callback, ChannelWarningSendEvent)

    async def listen_automod_message_hold(self,
                                          broadcaster_user_id: str,
                                          moderator_user_id: str,
                                          callback: Callable[[AutomodMessageHoldEvent], Awaitable[None]]) -> str:
        """Sends a notification if a message was caught by automod for review.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_AUTOMOD` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#automodmessagehold

        :param broadcaster_user_id: User ID of the broadcaster (channel).
        :param moderator_user_id: User ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('automod.message.hold', '1', param , callback, AutomodMessageHoldEvent)

    async def listen_automod_message_update(self,
                                            broadcaster_user_id: str,
                                            moderator_user_id: str,
                                            callback: Callable[[AutomodMessageUpdateEvent], Awaitable[None]]) -> str:
        """Sends a notification when a message in the automod queue has its status changed.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_AUTOMOD` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#automodmessageupdate

        :param broadcaster_user_id: User ID of the broadcaster (channel)
        :param moderator_user_id: User ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('automod.message.update', '1', param, callback, AutomodMessageUpdateEvent)

    async def listen_automod_settings_update(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: Callable[[AutomodSettingsUpdateEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster's automod settings are updated.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_READ_AUTOMOD_SETTINGS` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#automodsettingsupdate

        :param broadcaster_user_id: User ID of the broadcaster (channel).
        :param moderator_user_id: User ID of the moderator.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('automod.settings.update', '1', param, callback, AutomodSettingsUpdateEvent)

    async def listen_automod_terms_update(self,
                                          broadcaster_user_id: str,
                                          moderator_user_id: str,
                                          callback: Callable[[AutomodTermsUpdateEvent], Awaitable[None]]) -> str:
        """Sends a notification when a broadcaster's automod terms are updated.

        Requires :const:`~twitchAPI.type.AuthScope.MODERATOR_MANAGE_AUTOMOD` scope.

        .. note:: If you use webhooks, the user in moderator_user_id must have granted your app (client ID) one of the above permissions prior to your app subscribing to this subscription type.

                  If you use WebSockets, the ID in moderator_user_id must match the user ID in the user access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#automodtermsupdate

        :param broadcaster_user_id: User ID of the broadcaster (channel).
        :param moderator_user_id: User ID of the moderator creating the subscription.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('automod.terms.update', '1', param, callback, AutomodTermsUpdateEvent)

    async def listen_channel_chat_user_message_hold(self,
                                                    broadcaster_user_id: str,
                                                    user_id: str,
                                                    callback: Callable[[ChannelChatUserMessageHoldEvent], Awaitable[None]]) -> str:
        """A user is notified if their message is caught by automod.

        .. note:: Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from the chatting user.

                  If WebSockets is used, additionally requires :const:`~twitchAPI.type.AuthScope.USER_BOT` from chatting user.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatuser_message_hold

        :param broadcaster_user_id: User ID of the channel to receive chat message events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.user_message_hold', '1', param, callback, ChannelChatUserMessageHoldEvent)

    async def listen_channel_chat_user_message_update(self,
                                                      broadcaster_user_id: str,
                                                      user_id: str,
                                                      callback: Callable[[ChannelChatUserMessageUpdateEvent], Awaitable[None]]) -> str:
        """A user is notified if their message’s automod status is updated.

        .. note:: Requires :const:`~twitchAPI.type.AuthScope.USER_READ_CHAT` scope from the chatting user.

                  If WebSockets is used, additionally requires :const:`~twitchAPI.type.AuthScope.USER_BOT` from chatting user.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchatuser_message_update

        :param broadcaster_user_id: User ID of the channel to receive chat message events for.
        :param user_id: The user ID to read chat as.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'user_id': user_id
        }
        return await self._subscribe('channel.chat.user_message_update', '1', param, callback, ChannelChatUserMessageUpdateEvent)

    async def listen_channel_shared_chat_begin(self,
                                               broadcaster_user_id: str,
                                               callback: Callable[[ChannelSharedChatBeginEvent], Awaitable[None]]) -> str:
        """A notification when a channel becomes active in an active shared chat session.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshared_chatbegin

        :param broadcaster_user_id: The User ID of the channel to receive shared chat session begin events for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
        }
        return await self._subscribe('channel.shared_chat.begin', '1', param, callback, ChannelSharedChatBeginEvent)

    async def listen_channel_shared_chat_update(self,
                                                broadcaster_user_id: str,
                                                callback: Callable[[ChannelSharedChatUpdateEvent], Awaitable[None]]) -> str:
        """A notification when the active shared chat session the channel is in changes.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshared_chatupdate

        :param broadcaster_user_id: The User ID of the channel to receive shared chat session update events for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
        }
        return await self._subscribe('channel.shared_chat.update', '1', param, callback, ChannelSharedChatUpdateEvent)

    async def listen_channel_shared_chat_end(self,
                                             broadcaster_user_id: str,
                                             callback: Callable[[ChannelSharedChatEndEvent], Awaitable[None]]) -> str:
        """A notification when a channel leaves a shared chat session or the session ends.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshared_chatend

        :param broadcaster_user_id: The User ID of the channel to receive shared chat session end events for.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
        }
        return await self._subscribe('channel.shared_chat.end', '1', param, callback, ChannelSharedChatEndEvent)

    async def listen_channel_bits_use(self,
                                      broadcaster_user_id: str,
                                      callback: Callable[[ChannelBitsUseEvent], Awaitable[None]]) -> str:
        """A notification is sent whenever Bits are used on a channel.

         For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelbitsuse

        :param broadcaster_user_id: The user ID of the channel broadcaster.
        :param callback: function for callback
        :raises ~twitchAPI.type.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.type.EventSubSubscriptionTimeout: if :const:`~twitchAPI.eventsub.webhook.EventSubWebhook.wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.type.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.type.TwitchBackendException: if the subscription failed due to a twitch backend error
        :returns: The id of the topic subscription
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
        }
        return await self._subscribe('channel.bits.use', '1', param, callback, ChannelBitsUseEvent)
