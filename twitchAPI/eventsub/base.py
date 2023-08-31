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
                                       CharityCampaignStopEvent, CharityDonationEvent, ChannelShoutoutCreateEvent, ChannelShoutoutReceiveEvent)
from twitchAPI.helper import remove_none_values
from twitchAPI.type import TwitchAPIException
import asyncio
from logging import getLogger, Logger
from twitchAPI.twitch import Twitch
from abc import ABC, abstractmethod

from typing import Union, Callable, Optional, Awaitable

__all__ = ['EventSubBase']


class EventSubBase(ABC):
    """EventSub integration for the Twitch Helix API."""

    def __init__(self,
                 twitch: Twitch):
        """
        :param twitch: a app authenticated instance of :const:`~twitchAPI.twitch.Twitch`
        """
        self._twitch: Twitch = twitch
        self.logger: Logger = getLogger('twitchAPI.eventsub')
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
    def _get_transport(self):
        pass

    # ==================================================================================================================
    # HELPER
    # ==================================================================================================================

    @abstractmethod
    def _build_request_header(self):
        pass

    async def _api_post_request(self, session, url: str, data: Union[dict, None] = None):
        headers = self._build_request_header()
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
        ret = await self._twitch.get_eventsub_subscriptions()
        async for d in ret:
            try:
                await self._twitch.delete_eventsub_subscription(d.id)
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {d.id}: {str(e)}')
        self._callbacks.clear()

    async def unsubscribe_all_known(self):
        """Unsubscribe from all subscriptions known to this client."""
        for key, value in self._callbacks.items():
            self.logger.debug(f'unsubscribe from event {key}')
            try:
                await self._twitch.delete_eventsub_subscription(key)
            except TwitchAPIException as e:
                self.logger.warning(f'failed to unsubscribe from event {key}: {str(e)}')
        self._callbacks.clear()

    @abstractmethod
    async def _unsubscribe_hook(self, topic_id: str) -> bool:
        pass

    async def unsubscribe_topic(self, topic_id: str) -> bool:
        """Unsubscribe from a specific topic."""
        try:
            await self._twitch.delete_eventsub_subscription(topic_id)
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
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.update', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelUpdateEvent)

    async def listen_channel_update_v2(self, broadcaster_user_id: str, callback: Callable[[ChannelUpdateEvent], Awaitable[None]]) -> str:
        """A broadcaster updates their channel properties e.g., category, title, content classification labels or language.

        No Authentication required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.update', '2', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelUpdateEvent)

    async def listen_channel_follow(self, broadcaster_user_id: str, callback: Callable[[ChannelFollowEvent], Awaitable[None]]) -> str:
        """A specified channel receives a follow.

        .. warning:: This subscription is deprecated and will be removed on or soon after the 3rd of August 2023\n
            Please use :const:`~twitchAPI.eventsub.EventSub.listen_channel_follow_v2()`

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.follow', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelFollowEvent)

    async def listen_channel_follow_v2(self,
                                       broadcaster_user_id: str,
                                       moderator_user_id: str,
                                       callback: Callable[[ChannelFollowEvent], Awaitable[None]]) -> str:
        """A specified channel receives a follow.

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_FOLLOWERS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow

        :param broadcaster_user_id: the id of the user you want to listen to
        :param moderator_user_id: The ID of the moderator of the channel you want to get follow notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.follow',
                                     '2',
                                     {'broadcaster_user_id': broadcaster_user_id, 'moderator_user_id': moderator_user_id},
                                     callback,
                                     ChannelFollowEvent)

    async def listen_channel_subscribe(self, broadcaster_user_id: str, callback: Callable[[ChannelSubscribeEvent], Awaitable[None]]) -> str:
        """A notification when a specified channel receives a subscriber. This does not include resubscribes.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscribe

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscribe', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelSubscribeEvent)

    async def listen_channel_subscription_end(self,
                                              broadcaster_user_id: str,
                                              callback: Callable[[ChannelSubscriptionEndEvent], Awaitable[None]]) -> str:
        """A notification when a subscription to the specified channel ends.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.end', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelSubscriptionEndEvent)

    async def listen_channel_subscription_gift(self,
                                               broadcaster_user_id: str,
                                               callback: Callable[[ChannelSubscriptionGiftEvent], Awaitable[None]]) -> str:
        """A notification when a viewer gives a gift subscription to one or more users in the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptiongift

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.gift', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelSubscriptionGiftEvent)

    async def listen_channel_subscription_message(self,
                                                  broadcaster_user_id: str,
                                                  callback: Callable[[ChannelSubscriptionMessageEvent], Awaitable[None]]) -> str:
        """A notification when a user sends a resubscription chat message in a specific channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_SUBSCRIPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionmessage

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.subscription.message',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelSubscriptionMessageEvent)

    async def listen_channel_cheer(self, broadcaster_user_id: str, callback: Callable[[ChannelCheerEvent], Awaitable[None]]) -> str:
        """A user cheers on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.BITS_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelcheer

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.ban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelBanEvent)

    async def listen_channel_unban(self, broadcaster_user_id: str, callback: Callable[[ChannelUnbanEvent], Awaitable[None]]) -> str:
        """A viewer is unbanned from the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_MODERATE` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelunban

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.unban',
                                     '1',
                                     {'broadcaster_user_id': broadcaster_user_id},
                                     callback,
                                     ChannelUnbanEvent)

    async def listen_channel_moderator_add(self, broadcaster_user_id: str, callback: Callable[[ChannelModeratorAddEvent], Awaitable[None]]) -> str:
        """Moderator privileges were added to a user on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatoradd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.MODERATION_READ` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatorremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardremove

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionadd

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_REDEMPTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_REDEMPTIONS` is required.

        For more information see here:
        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionupdate

        :param broadcaster_user_id: the id of the user you want to listen to
        :param reward_id: the id of the reward you want to get updates from. |default| :code:`None`
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollBeginEvent)

    async def listen_channel_poll_progress(self, broadcaster_user_id: str, callback: Callable[[ChannelPollProgressEvent], Awaitable[None]]) -> str:
        """Users respond to a poll on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollProgressEvent)

    async def listen_channel_poll_end(self, broadcaster_user_id: str, callback: Callable[[ChannelPollEndEvent], Awaitable[None]]) -> str:
        """A poll ended on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_POLLS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_POLLS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.poll.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     ChannelPollEndEvent)

    async def listen_channel_prediction_begin(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """A Prediction started on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.begin', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_progress(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """Users participated in a Prediction on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.progress', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_lock(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEvent], Awaitable[None]]) -> str:
        """A Prediction was locked on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionlock

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.prediction.lock', '1', {'broadcaster_user_id': broadcaster_user_id},
                                     callback, ChannelPredictionEvent)

    async def listen_channel_prediction_end(self, broadcaster_user_id: str, callback: Callable[[ChannelPredictionEndEvent], Awaitable[None]]) -> str:
        """A Prediction ended on a specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_PREDICTIONS` or
        :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_PREDICTIONS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('extension.bits_transaction.create', '1', {'extension_client_id': extension_client_id}, callback,
                                     ExtensionBitsTransactionCreateEvent)

    async def listen_goal_begin(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal begins on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_goal_progress(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_goal_end(self, broadcaster_user_id: str, callback: Callable[[GoalEvent], Awaitable[None]]) -> str:
        """A goal ends on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_GOALS` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelgoalend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.goal.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     GoalEvent)

    async def listen_hype_train_begin(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEvent], Awaitable[None]]) -> str:
        """A Hype Train begins on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainbegin

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.begin', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEvent)

    async def listen_hype_train_progress(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEvent], Awaitable[None]]) -> str:
        """A Hype Train makes progress on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainprogress

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.progress', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEvent)

    async def listen_hype_train_end(self, broadcaster_user_id: str, callback: Callable[[HypeTrainEndEvent], Awaitable[None]]) -> str:
        """A Hype Train ends on the specified channel.

        User Authentication with :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_HYPE_TRAIN` is required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainend

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('channel.hype_train.end', '1', {'broadcaster_user_id': broadcaster_user_id}, callback,
                                     HypeTrainEndEvent)

    async def listen_stream_online(self, broadcaster_user_id: str, callback: Callable[[StreamOnlineEvent], Awaitable[None]]) -> str:
        """The specified broadcaster starts a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamonline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('stream.online', '1', {'broadcaster_user_id': broadcaster_user_id}, callback, StreamOnlineEvent)

    async def listen_stream_offline(self, broadcaster_user_id: str, callback: Callable[[StreamOfflineEvent], Awaitable[None]]) -> str:
        """The specified broadcaster stops a stream.

        No authorization required.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamoffline

        :param broadcaster_user_id: the id of the user you want to listen to
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('stream.offline', '1', {'broadcaster_user_id': broadcaster_user_id}, callback, StreamOfflineEvent)

    async def listen_user_authorization_grant(self, client_id: str, callback: Callable[[UserAuthorizationGrantEvent], Awaitable[None]]) -> str:
        """A user’s authorization has been granted to your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationgrant

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.authorization.grant', '1', {'client_id': client_id}, callback,
                                     UserAuthorizationGrantEvent)

    async def listen_user_authorization_revoke(self, client_id: str, callback: Callable[[UserAuthorizationRevokeEvent], Awaitable[None]]) -> str:
        """A user’s authorization has been revoked for your client id.

        Provided client_id must match the client id in the application access token.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationrevoke

        :param client_id: Your application’s client id.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.authorization.revoke', '1', {'client_id': client_id}, callback,
                                     UserAuthorizationRevokeEvent)

    async def listen_user_update(self, user_id: str, callback: Callable[[UserUpdateEvent], Awaitable[None]]) -> str:
        """A user has updated their account.

        No authorization required. If you have the :const:`~twitchAPI.types.AuthScope.USER_READ_EMAIL` scope,
        the notification will include email field.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userupdate

        :param user_id: The user ID for the user you want update notifications for.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        return await self._subscribe('user.update', '1', {'user_id': user_id}, callback, UserUpdateEvent)

    async def listen_channel_shield_mode_begin(self,
                                               broadcaster_user_id: str,
                                               moderator_user_id: str,
                                               callback: Callable[[ShieldModeEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster activates Shield Mode.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modebegin

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they activate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHIELD_MODE` or
        :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHIELD_MODE` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshield_modeend

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they deactivate Shield Mode.
        :param moderator_user_id: The ID of the broadcaster or one of the broadcaster’s moderators.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
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

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstart

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they start a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.start', '1', param, callback, CharityCampaignStartEvent)

    async def listen_channel_charity_campaign_progress(self,
                                                       broadcaster_user_id: str,
                                                       callback: Callable[[CharityCampaignProgressEvent], Awaitable[None]]) -> str:
        """Sends notifications when progress is made towards the campaign’s goal or when the broadcaster changes the fundraising goal.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignprogress

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when their campaign makes progress or
                is updated.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.progress', '1', param, callback, CharityCampaignProgressEvent)

    async def listen_channel_charity_campaign_stop(self,
                                                   broadcaster_user_id: str,
                                                   callback: Callable[[CharityCampaignStopEvent], Awaitable[None]]) -> str:
        """Sends a notification when the broadcaster stops a charity campaign.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaignstop

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they stop a charity campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.stop', '1', param, callback, CharityCampaignStopEvent)

    async def listen_channel_charity_campaign_donate(self,
                                                     broadcaster_user_id: str,
                                                     callback: Callable[[CharityDonationEvent], Awaitable[None]]) -> str:
        """Sends a notification when a user donates to the broadcaster’s charity campaign.

        Requires the :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY` auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelcharity_campaigndonate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when users donate to their campaign.
        :param callback: function for callback
        :raises ~twitchAPI.types.EventSubSubscriptionConflict: if a conflict was found with this subscription
            (e.g. already subscribed to this exact topic)
        :raises ~twitchAPI.types.EventSubSubscriptionTimeout: if :code:`wait_for_subscription_confirm`
            is true and the subscription was not fully confirmed in time
        :raises ~twitchAPI.types.EventSubSubscriptionError: if the subscription failed (see error message for details)
        :raises ~twitchAPI.types.TwitchBackendException: if the subscription failed due to a twitch backend error
        """
        param = {'broadcaster_user_id': broadcaster_user_id}
        return await self._subscribe('channel.charity_campaign.donate', '1', param, callback, CharityDonationEvent)

    async def listen_channel_shoutout_create(self,
                                             broadcaster_user_id: str,
                                             moderator_user_id: str,
                                             callback: Callable[[ChannelShoutoutCreateEvent], Awaitable[None]]) -> str:
        """Sends a notification when the specified broadcaster sends a Shoutout.

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutcreate

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they send a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that gave the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
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

        Requires the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHOUTOUTS` or :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
        auth scope.

        For more information see here: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelshoutoutreceive

        :param broadcaster_user_id: The ID of the broadcaster that you want to receive notifications about when they receive a Shoutout.
        :param moderator_user_id: The ID of the broadcaster that received the Shoutout or one of the broadcaster’s moderators.
        :param callback: function for callback
        """
        param = {
            'broadcaster_user_id': broadcaster_user_id,
            'moderator_user_id': moderator_user_id
        }
        return await self._subscribe('channel.shoutout.receive', '1', param, callback, ChannelShoutoutReceiveEvent)
