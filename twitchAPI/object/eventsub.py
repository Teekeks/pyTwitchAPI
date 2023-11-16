#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
Objects used by EventSub
------------------------
"""


from twitchAPI.object.base import TwitchObject
from datetime import datetime
from typing import List, Optional

__all__ = ['ChannelPollBeginEvent', 'ChannelUpdateEvent', 'ChannelFollowEvent', 'ChannelSubscribeEvent', 'ChannelSubscriptionEndEvent',
           'ChannelSubscriptionGiftEvent', 'ChannelSubscriptionMessageEvent', 'ChannelCheerEvent', 'ChannelRaidEvent', 'ChannelBanEvent',
           'ChannelUnbanEvent', 'ChannelModeratorAddEvent', 'ChannelModeratorRemoveEvent', 'ChannelPointsCustomRewardAddEvent',
           'ChannelPointsCustomRewardUpdateEvent', 'ChannelPointsCustomRewardRemoveEvent', 'ChannelPointsCustomRewardRedemptionAddEvent',
           'ChannelPointsCustomRewardRedemptionUpdateEvent', 'ChannelPollProgressEvent', 'ChannelPollEndEvent', 'ChannelPredictionEvent',
           'ChannelPredictionEndEvent', 'DropEntitlementGrantEvent', 'ExtensionBitsTransactionCreateEvent', 'GoalEvent', 'HypeTrainEvent',
           'HypeTrainEndEvent', 'StreamOnlineEvent', 'StreamOfflineEvent', 'UserAuthorizationGrantEvent', 'UserAuthorizationRevokeEvent',
           'UserUpdateEvent', 'ShieldModeEvent', 'CharityCampaignStartEvent', 'CharityCampaignProgressEvent', 'CharityCampaignStopEvent',
           'CharityDonationEvent', 'ChannelShoutoutCreateEvent', 'ChannelShoutoutReceiveEvent', 'ChannelChatClearEvent',
           'Subscription', 'ChannelPollBeginData', 'PollChoice', 'BitsVoting', 'ChannelPointsVoting', 'ChannelUpdateData', 'ChannelFollowData',
           'ChannelSubscribeData', 'ChannelSubscriptionEndData', 'ChannelSubscriptionGiftData', 'ChannelSubscriptionMessageData',
           'SubscriptionMessage', 'Emote', 'ChannelCheerData', 'ChannelRaidData', 'ChannelBanData', 'ChannelUnbanData', 'ChannelModeratorAddData',
           'ChannelModeratorRemoveData', 'ChannelPointsCustomRewardData', 'GlobalCooldown', 'Image', 'MaxPerStream', 'MaxPerUserPerStream',
           'ChannelPointsCustomRewardRedemptionData', 'Reward', 'ChannelPollProgressData', 'ChannelPollEndData', 'ChannelPredictionData', 'Outcome',
           'TopPredictors', 'ChannelPredictionEndData', 'DropEntitlementGrantData', 'Entitlement', 'Product', 'ExtensionBitsTransactionCreateData',
           'GoalData', 'TopContribution', 'LastContribution', 'HypeTrainData', 'HypeTrainEndData', 'StreamOnlineData', 'StreamOfflineData',
           'UserAuthorizationGrantData', 'UserAuthorizationRevokeData', 'UserUpdateData', 'ShieldModeData', 'Amount', 'CharityCampaignStartData',
           'CharityCampaignStopData', 'CharityCampaignProgressData', 'CharityDonationData', 'ChannelShoutoutCreateData', 'ChannelShoutoutReceiveData',
           'ChannelChatClearData']


# Event Data

class Subscription(TwitchObject):
    condition: dict
    cost: int
    created_at: datetime
    id: str
    status: str
    transport: dict
    type: str
    version: str


class PollChoice(TwitchObject):
    id: str
    """ID for the choice"""
    title: str
    """Text displayed for the choice"""
    bits_votes: int
    """Not used; will be stet to 0"""
    channel_points_votes: int
    """Number of votes received via Channel Points"""
    votes: int
    """Total number of votes received for the choice across all methods of voting"""


class BitsVoting(TwitchObject):
    is_enabled: bool
    """Not used; will be set to False"""
    amount_per_vote: int
    """Not used; will be set to 0"""


class ChannelPointsVoting(TwitchObject):
    is_enabled: bool
    """Indicates if Channel Points can be used for Voting"""
    amount_per_vote: int
    """Number of Channel Points required to vote once with Channel Points"""


class ChannelPollBeginData(TwitchObject):
    id: str
    """ID of the poll"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    title: str
    """Question displayed for the poll"""
    choices: List[PollChoice]
    """Array of choices for the poll"""
    bits_voting: BitsVoting
    """Not supported"""
    channel_points_voting: ChannelPointsVoting
    """The Channel Points voting settings for the Poll"""
    started_at: datetime
    """The time the poll started"""
    ends_at: datetime
    """The time the poll will end"""


class ChannelUpdateData(TwitchObject):
    broadcaster_user_id: str
    """The broadcaster’s user ID"""
    broadcaster_user_login: str
    """The broadcaster’s user login"""
    broadcaster_user_name: str
    """The broadcaster’s user display name"""
    title: str
    """The channel’s stream title"""
    language: str
    """The channel’s broadcast language"""
    category_id: str
    """The channel´s category ID"""
    category_name: str
    """The category name"""
    content_classification_labels: List[str]
    """Array of classification label IDs currently applied to the Channel"""


class ChannelFollowData(TwitchObject):
    user_id: str
    """The user ID for the user now following the specified channel"""
    user_login: str
    """The user login for the user now following the specified channel"""
    user_name: str
    """The user display name for the user now following the specified channel"""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    followed_at: datetime
    """when the follow occured"""


class ChannelSubscribeData(TwitchObject):
    user_id: str
    """The user ID for the user who subscribed to the specified channel"""
    user_login: str
    """The user login for the user who subscribed to the specified channel"""
    user_name: str
    """The user display name for the user who subscribed to the specified channel"""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    tier: str
    """The tier of the subscription. Valid values are 1000, 2000, and 3000"""
    is_gift: bool
    """Whether the subscription is a gift"""


class ChannelSubscriptionEndData(TwitchObject):
    user_id: str
    """The user ID for the user whose subscription ended"""
    user_login: str
    """The user login for the user whose subscription ended"""
    user_name: str
    """The user display name for the user whose subscription ended"""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    tier: str
    """The tier of the subscription that ended. Valid values are 1000, 2000, and 3000"""
    is_gift: bool
    """Whether the subscription was a gift"""


class ChannelSubscriptionGiftData(TwitchObject):
    user_id: Optional[str]
    """The user ID for the user who sent the subscription gift. None if it was an anonymous subscription gift."""
    user_login: Optional[str]
    """The user login for the user who sent the subscription gift. None if it was an anonymous subscription gift."""
    user_name: Optional[str]
    """The user display name for the user who sent the subscription gift. None if it was an anonymous subscription gift."""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    total: int
    """The number of subscriptions in teh subscription gift"""
    tier: str
    """The tier of the subscription that ended. Valid values are 1000, 2000, and 3000"""
    cumulative_total: Optional[int]
    """The number of subscriptions giftet by this user in teh channel. 
    None for anonymous gifts or if the gifter has opted out of sharing this information"""
    is_anonymous: bool
    """Whether the subscription gift was anonymous"""


class Emote(TwitchObject):
    begin: int
    """The index of where the Emote starts in the text"""
    end: int
    """The index of where the Emote ends in the text"""
    id: str
    """The emote ID"""


class SubscriptionMessage(TwitchObject):
    text: str
    """the text of the resubscription chat message"""
    emotes: List[Emote]
    """An array that includes the emote ID and start and end positions for where the emote appears in the text"""


class ChannelSubscriptionMessageData(TwitchObject):
    user_id: str
    """The user ID for the user who sent a resubscription chat message"""
    user_login: str
    """The user login for the user who sent a resubscription chat message"""
    user_name: str
    """The user display name for the user who sent a resubscription chat message"""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    tier: str
    """The tier of the user´s subscription"""
    message: SubscriptionMessage
    """An object that contains the resubscription message and emote information needed to recreate the message."""
    cumulative_months: Optional[int]
    """The number of consecutive months the user’s current subscription has been active. 
    None if the user has opted out of sharing this information."""
    duration_months: int
    """The month duration of the subscription"""


class ChannelCheerData(TwitchObject):
    is_anonymous: bool
    """Whether the user cheered anonymously or not"""
    user_id: Optional[str]
    """The user ID for the user who cheered on the specified channel. None if is_anonymous is True."""
    user_login: Optional[str]
    """The user login for the user who cheered on the specified channel. None if is_anonymous is True."""
    user_name: Optional[str]
    """The user display name for the user who cheered on the specified channel. None if is_anonymous is True."""
    broadcaster_user_id: str
    """The requested broadcaster’s user ID"""
    broadcaster_user_login: str
    """The requested broadcaster’s user login"""
    broadcaster_user_name: str
    """The requested broadcaster’s user display name"""
    message: str
    """The message sent with the cheer"""
    bits: int
    """The number of bits cheered"""


class ChannelRaidData(TwitchObject):
    from_broadcaster_user_id: str
    """The broadcaster id that created the raid"""
    from_broadcaster_user_login: str
    """The broadcaster login that created the raid"""
    from_broadcaster_user_name: str
    """The broadcaster display name that created the raid"""
    to_broadcaster_user_id: str
    """The broadcaster id that received the raid"""
    to_broadcaster_user_login: str
    """The broadcaster login that received the raid"""
    to_broadcaster_user_name: str
    """The broadcaster display name that received the raid"""
    viewers: int
    """The number of viewers in the raid"""


class ChannelBanData(TwitchObject):
    user_id: str
    """The user ID for the user who was banned on the specified channel"""
    user_login: str
    """The user login for the user who was banned on the specified channel"""
    user_name: str
    """The user display name for the user who was banned on the specified channel"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    moderator_user_id: str
    """The user ID of the issuer of the ban"""
    moderator_user_login: str
    """The user login of the issuer of the ban"""
    moderator_user_name: str
    """The user display name of the issuer of the ban"""
    reason: str
    """The reason behind the ban"""
    banned_at: datetime
    """The timestamp of when the user was banned or put in a timeout"""
    ends_at: Optional[datetime]
    """The timestamp of when the timeout ends. None if the user was banned instead of put in a timeout."""
    is_permanent: bool
    """Indicates whether the ban is permanent (True) or a timeout (False). If True, ends_at will be None."""


class ChannelUnbanData(TwitchObject):
    user_id: str
    """The user ID for the user who was unbanned on the specified channel"""
    user_login: str
    """The user login for the user who was unbanned on the specified channel"""
    user_name: str
    """The user display name for the user who was unbanned on the specified channel"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    moderator_user_id: str
    """The user ID of the issuer of the unban"""
    moderator_user_login: str
    """The user login of the issuer of the unban"""
    moderator_user_name: str
    """The user display name of the issuer of the unban"""


class ChannelModeratorAddData(TwitchObject):
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    user_id: str
    """The user ID of the new moderator"""
    user_login: str
    """The user login of the new moderator"""
    user_name: str
    """The user display name of the new moderator"""


class ChannelModeratorRemoveData(TwitchObject):
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    user_id: str
    """The user ID of the removed moderator"""
    user_login: str
    """The user login of the removed moderator"""
    user_name: str
    """The user display name of the removed moderator"""


class MaxPerStream(TwitchObject):
    is_enabled: bool
    """Is the setting enabled"""
    value: int
    """The max per stream limit"""


class MaxPerUserPerStream(TwitchObject):
    is_enabled: bool
    """Is the setting enabled"""
    value: int
    """The max per user per stream limit"""


class Image(TwitchObject):
    url_1x: str
    """URL for the image at 1x size"""
    url_2x: str
    """URL for the image at 2x size"""
    url_4x: str
    """URL for the image at 4x size"""


class GlobalCooldown(TwitchObject):
    is_enabled: bool
    """Is the setting enabled"""
    seconds: int
    """The cooldown in seconds"""


class ChannelPointsCustomRewardData(TwitchObject):
    id: str
    """The reward identifier"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    is_enabled: bool
    """Is the reward currently enabled. If False, the reward won't show up to viewers."""
    is_paused: bool
    """Is the reward currently paused. If True, viewers can't redeem."""
    is_in_stock: bool
    """Is the reward currently in stock. If False, viewers can't redeem."""
    title: str
    """The reward title"""
    cost: int
    """The reward cost"""
    prompt: str
    """The reward description"""
    is_user_input_required: bool
    """Does the viewer need to enter information when redeeming the reward"""
    should_redemptions_skip_request_queue: bool
    """Should redemptions be set to :code:`fulfilled` status immediately when redeemed and skip the request queue instead of the normal 
    :code:`unfulfilled` status."""
    max_per_stream: MaxPerStream
    """Whether a maximum per stream is enabled and what the maximum is"""
    max_per_user_per_stream: MaxPerUserPerStream
    """Whether a maximum per user per stream is enabled and what the maximum is"""
    background_color: str
    """Custom background color for the reward. Format: Hex with # prefix."""
    image: Optional[Image]
    """Set of custom images for the reward. None if no images have been uploaded"""
    default_image: Image
    """Set of default images for the reward"""
    global_cooldown: GlobalCooldown
    """Whether a cooldown is enabled and what the cooldown is in seconds"""
    cooldown_expires_at: Optional[datetime]
    """Timestamp of the cooldown expiration. None if the reward is not on cooldown."""
    redemptions_redeemed_current_stream: Optional[int]
    """The number of redemptions redeemed during the current live stream. Counts against the max_per_stream limit. 
    None if the broadcasters stream is not live or max_per_stream isn not enabled."""


class Reward(TwitchObject):
    id: str
    """The reward identifier"""
    title: str
    """The reward name"""
    cost: int
    """The reward cost"""
    prompt: str
    """The reward description"""


class ChannelPointsCustomRewardRedemptionData(TwitchObject):
    id: str
    """The redemption identifier"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    user_id: str
    """User ID of the user the redeemed the reward"""
    user_login: str
    """Login of the user the redeemed the reward"""
    user_name: str
    """Display name of the user the redeemed the reward"""
    user_input: str
    """The user input provided. Empty if not provided."""
    status: str
    """Defaults to :code:`unfulfilled`. Possible values are: :code:`unknown`, :code:`unfulfilled`, :code:`fulfilled` and :code:`canceled`"""
    reward: Reward
    """Basic information about the reward that was redeemed, at the time it was redeemed"""
    redeemed_at: datetime
    """Timestamp of when the reward was redeemed"""


class ChannelPollProgressData(TwitchObject):
    id: str
    """ID of the poll"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    title: str
    """Question displayed for the poll"""
    choices: List[PollChoice]
    """An array of choices for the poll. Includes vote counts."""
    bits_voting: BitsVoting
    """not supported"""
    channel_points_voting: ChannelPointsVoting
    """The Channel Points voting settings for the poll"""
    started_at: datetime
    """The time the poll started"""
    ends_at: datetime
    """The time the poll will end"""


class ChannelPollEndData(TwitchObject):
    id: str
    """ID of the poll"""
    broadcaster_user_id: str
    """The requested broadcaster ID"""
    broadcaster_user_login: str
    """The requested broadcaster login"""
    broadcaster_user_name: str
    """The requested broadcaster display name"""
    title: str
    """Question displayed for the poll"""
    choices: List[PollChoice]
    """An array of choices for the poll. Includes vote counts."""
    bits_voting: BitsVoting
    """not supported"""
    channel_points_voting: ChannelPointsVoting
    """The Channel Points voting settings for the poll"""
    status: str
    """The status of the poll. Valid values are completed, archived and terminated."""
    started_at: datetime
    """The time the poll started"""
    ends_at: datetime
    """The time the poll ended"""


class TopPredictors(TwitchObject):
    user_id: str
    """The ID of the user."""
    user_login: str
    """The login of the user."""
    user_name: str
    """The display name of the user."""
    channel_points_won: int
    """The number of Channel Points won. This value is always null in the event payload for Prediction progress and Prediction lock. This value is 0 
    if the outcome did not win or if the Prediction was canceled and Channel Points were refunded."""
    channel_points_used: int
    """The number of Channel Points used to participate in the Prediction."""


class Outcome(TwitchObject):
    id: str
    """The outcome ID."""
    title: str
    """The outcome title."""
    color: str
    """The color for the outcome. Valid values are pink and blue."""
    users: int
    """The number of users who used Channel Points on this outcome."""
    channel_points: int
    """The total number of Channel Points used on this outcome."""
    top_predictors: TopPredictors
    """An array of users who used the most Channel Points on this outcome."""


class ChannelPredictionData(TwitchObject):
    id: str
    """Channel Points Prediction ID."""
    broadcaster_user_id: str
    """The requested broadcaster ID."""
    broadcaster_user_login: str
    """The requested broadcaster login."""
    broadcaster_user_name: str
    """The requested broadcaster display name."""
    title: str
    """Title for the Channel Points Prediction."""
    outcomes: List[Outcome]
    """An array of outcomes for the Channel Points Prediction."""
    started_at: datetime
    """The time the Channel Points Prediction started."""
    locks_at: datetime
    """The time the Channel Points Prediction will automatically lock."""


class ChannelPredictionEndData(TwitchObject):
    id: str
    """Channel Points Prediction ID."""
    broadcaster_user_id: str
    """The requested broadcaster ID."""
    broadcaster_user_login: str
    """The requested broadcaster login."""
    broadcaster_user_name: str
    """The requested broadcaster display name."""
    title: str
    """Title for the Channel Points Prediction."""
    winning_outcome_id: str
    """ID of the winning outcome."""
    outcomes: List[Outcome]
    """An array of outcomes for the Channel Points Prediction. Includes top_predictors."""
    status: str
    """The status of the Channel Points Prediction. Valid values are resolved and canceled."""
    started_at: datetime
    """The time the Channel Points Prediction started."""
    ended_at: datetime
    """The time the Channel Points Prediction ended."""


class Entitlement(TwitchObject):
    organization_id: str
    """The ID of the organization that owns the game that has Drops enabled."""
    category_id: str
    """Twitch category ID of the game that was being played when this benefit was entitled."""
    category_name: str
    """The category name."""
    campaign_id: str
    """The campaign this entitlement is associated with."""
    user_id: str
    """Twitch user ID of the user who was granted the entitlement."""
    user_name: str
    """The user display name of the user who was granted the entitlement."""
    user_login: str
    """The user login of the user who was granted the entitlement."""
    entitlement_id: str
    """Unique identifier of the entitlement. Use this to de-duplicate entitlements."""
    benefit_id: str
    """Identifier of the Benefit."""
    created_at: datetime
    """UTC timestamp in ISO format when this entitlement was granted on Twitch."""


class DropEntitlementGrantData(TwitchObject):
    id: str
    """Individual event ID, as assigned by EventSub. Use this for de-duplicating messages."""
    data: Entitlement
    """Entitlement object"""


class Product(TwitchObject):
    name: str
    """Product name."""
    bits: int
    """Bits involved in the transaction."""
    sku: str
    """Unique identifier for the product acquired."""
    in_development: bool
    """Flag indicating if the product is in development. If in_development is true, bits will be 0."""


class ExtensionBitsTransactionCreateData(TwitchObject):
    extension_client_id: str
    """Client ID of the extension."""
    id: str
    """Transaction ID."""
    broadcaster_user_id: str
    """The transaction’s broadcaster ID."""
    broadcaster_user_login: str
    """The transaction’s broadcaster login."""
    broadcaster_user_name: str
    """The transaction’s broadcaster display name."""
    user_id: str
    """The transaction’s user ID."""
    user_login: str
    """The transaction’s user login."""
    user_name: str
    """The transaction’s user display name."""
    product: Product
    """Additional extension product information."""


class GoalData(TwitchObject):
    id: str
    """An ID that identifies this event."""
    broadcaster_user_id: str
    """An ID that uniquely identifies the broadcaster."""
    broadcaster_user_name: str
    """The broadcaster’s display name."""
    broadcaster_user_login: str
    """The broadcaster’s user handle."""
    type: str
    """The type of goal. Possible values are:
    
    - follow — The goal is to increase followers.
    - subscription — The goal is to increase subscriptions. This type shows the net increase or decrease in tier points associated with the 
      subscriptions.
    - subscription_count — The goal is to increase subscriptions. This type shows the net increase or decrease in the number of subscriptions.
    - new_subscription — The goal is to increase subscriptions. This type shows only the net increase in tier points associated with the subscriptions
      (it does not account for users that unsubscribed since the goal started).
    - new_subscription_count — The goal is to increase subscriptions. This type shows only the net increase in the number of subscriptions 
      (it does not account for users that unsubscribed since the goal started).
    """
    description: str
    """A description of the goal, if specified. The description may contain a maximum of 40 characters."""
    is_achieved: Optional[bool]
    """A Boolean value that indicates whether the broadcaster achieved their goal. Is true if the goal was achieved; otherwise, false.
    Only the channel.goal.end event includes this field."""
    current_amount: int
    """The goals current value. The goals type determines how this value is increased or decreased
    
    - If type is follow, this field is set to the broadcaster's current number of followers. This number increases with new followers and decreases 
      when users unfollow the broadcaster.
    - If type is subscription, this field is increased and decreased by the points value associated with the subscription tier. For example, if a 
      tier-two subscription is worth 2 points, this field is increased or decreased by 2, not 1.
    - If type is subscription_count, this field is increased by 1 for each new subscription and decreased by 1 for each user that unsubscribes.
    - If type is new_subscription, this field is increased by the points value associated with the subscription tier. For example, if a tier-two 
      subscription is worth 2 points, this field is increased by 2, not 1.
    - If type is new_subscription_count, this field is increased by 1 for each new subscription."""
    target_amount: int
    """The goal’s target value. For example, if the broadcaster has 200 followers before creating the goal, and their goal is to double that number, 
    this field is set to 400."""
    started_at: datetime
    """The timestamp which indicates when the broadcaster created the goal."""
    ended_at: Optional[datetime]
    """The timestamp which indicates when the broadcaster ended the goal. Only the channel.goal.end event includes this field."""


class TopContribution(TwitchObject):
    user_id: str
    """The ID of the user that made the contribution."""
    user_login: str
    """The user’s login name."""
    user_name: str
    """The user’s display name."""
    type: str
    """The contribution method used. Possible values are:
    
    - bits — Cheering with Bits.
    - subscription — Subscription activity like subscribing or gifting subscriptions.
    - other — Covers other contribution methods not listed."""
    total: int
    """The total amount contributed. If type is bits, total represents the amount of Bits used. If type is subscription, total is 500, 1000, or 2500 
    to represent tier 1, 2, or 3 subscriptions, respectively."""


class LastContribution(TwitchObject):
    user_id: str
    """The ID of the user that made the contribution."""
    user_login: str
    """The user’s login name."""
    user_name: str
    """The user’s display name."""
    type: str
    """The contribution method used. Possible values are:
    
    - bits — Cheering with Bits.
    - subscription — Subscription activity like subscribing or gifting subscriptions.
    - other — Covers other contribution methods not listed."""
    total: int
    """The total amount contributed. If type is bits, total represents the amount of Bits used. If type is subscription, total is 500, 1000, or 2500 
    to represent tier 1, 2, or 3 subscriptions, respectively."""


class HypeTrainData(TwitchObject):
    id: str
    """The Hype Train ID."""
    broadcaster_user_id: str
    """The requested broadcaster ID."""
    broadcaster_user_login: str
    """The requested broadcaster login."""
    broadcaster_user_name: str
    """The requested broadcaster display name."""
    total: int
    """Total points contributed to the Hype Train."""
    progress: int
    """The number of points contributed to the Hype Train at the current level."""
    goal: int
    """The number of points required to reach the next level."""
    top_contributions: List[TopContribution]
    """The contributors with the most points contributed."""
    last_contribution: LastContribution
    """The most recent contribution."""
    level: int
    """The starting level of the Hype Train."""
    started_at: datetime
    """The time when the Hype Train started."""
    expires_at: datetime
    """The time when the Hype Train expires. The expiration is extended when the Hype Train reaches a new level."""


class HypeTrainEndData(TwitchObject):
    id: str
    """The Hype Train ID."""
    broadcaster_user_id: str
    """The requested broadcaster ID."""
    broadcaster_user_login: str
    """The requested broadcaster login."""
    broadcaster_user_name: str
    """The requested broadcaster display name."""
    level: int
    """The final level of the Hype Train."""
    total: int
    """Total points contributed to the Hype Train."""
    top_contributions: List[TopContribution]
    """The contributors with the most points contributed."""
    started_at: datetime
    """The time when the Hype Train started."""
    ended_at: datetime
    """The time when the Hype Train ended."""
    cooldown_ends_at: datetime
    """The time when the Hype Train cooldown ends so that the next Hype Train can start."""


class StreamOnlineData(TwitchObject):
    id: str
    """The id of the stream."""
    broadcaster_user_id: str
    """The broadcaster’s user id."""
    broadcaster_user_login: str
    """The broadcaster’s user login."""
    broadcaster_user_name: str
    """The broadcaster’s user display name."""
    type: str
    """The stream type. Valid values are: live, playlist, watch_party, premiere, rerun."""
    started_at: datetime
    """The timestamp at which the stream went online at."""


class StreamOfflineData(TwitchObject):
    broadcaster_user_id: str
    """The broadcaster’s user id."""
    broadcaster_user_login: str
    """The broadcaster’s user login."""
    broadcaster_user_name: str
    """The broadcaster’s user display name."""


class UserAuthorizationGrantData(TwitchObject):
    client_id: str
    """The client_id of the application that was granted user access."""
    user_id: str
    """The user id for the user who has granted authorization for your client id."""
    user_login: str
    """The user login for the user who has granted authorization for your client id."""
    user_name: str
    """The user display name for the user who has granted authorization for your client id."""


class UserAuthorizationRevokeData(TwitchObject):
    client_id: str
    """The client_id of the application with revoked user access."""
    user_id: str
    """The user id for the user who has revoked authorization for your client id."""
    user_login: str
    """The user login for the user who has revoked authorization for your client id. This is null if the user no longer exists."""
    user_name: str
    """The user display name for the user who has revoked authorization for your client id. This is null if the user no longer exists."""


class UserUpdateData(TwitchObject):
    user_id: str
    """The user’s user id."""
    user_login: str
    """The user’s user login."""
    user_name: str
    """The user’s user display name."""
    email: str
    """The user’s email address. The event includes the user’s email address only if the app used to request this event type includes the 
    user:read:email scope for the user; otherwise, the field is set to an empty string. See Create EventSub Subscription."""
    email_verified: bool
    """A Boolean value that determines whether Twitch has verified the user’s email address. Is true if Twitch has verified the email address; 
    otherwise, false.

    NOTE: Ignore this field if the email field contains an empty string."""


class ShieldModeData(TwitchObject):
    broadcaster_user_id: str
    """An ID that identifies the broadcaster whose Shield Mode status was updated."""
    broadcaster_user_login: str
    """The broadcaster’s login name."""
    broadcaster_user_name: str
    """The broadcaster’s display name."""
    moderator_user_id: str
    """An ID that identifies the moderator that updated the Shield Mode’s status. If the broadcaster updated the status, this ID will be the same 
    as broadcaster_user_id."""
    moderator_user_login: str
    """The moderator’s login name."""
    moderator_user_name: str
    """The moderator’s display name."""
    started_at: datetime
    """The timestamp of when the moderator activated Shield Mode. The object includes this field only for 
    channel.shield_mode.begin events."""
    ended_at: datetime
    """The timestamp of when the moderator deactivated Shield Mode. The object includes this field only for 
    channel.shield_mode.end events."""


class Amount(TwitchObject):
    value: int
    """The monetary amount. The amount is specified in the currency’s minor unit. For example, the minor units for USD is cents, so if the amount 
    is $5.50 USD, value is set to 550."""
    decimal_places: int
    """The number of decimal places used by the currency. For example, USD uses two decimal places. Use this number to translate value from minor 
    units to major units by using the formula:

    value / 10^decimal_places"""
    currency: str
    """The ISO-4217 three-letter currency code that identifies the type of currency in value."""


class CharityCampaignStartData(TwitchObject):
    id: str
    """An ID that identifies the charity campaign."""
    broadcaster_id: str
    """An ID that identifies the broadcaster that’s running the campaign."""
    broadcaster_login: str
    """The broadcaster’s login name."""
    broadcaster_name: str
    """The broadcaster’s display name."""
    charity_name: str
    """The charity’s name."""
    charity_description: str
    """A description of the charity."""
    charity_logo: str
    """A URL to an image of the charity’s logo. The image’s type is PNG and its size is 100px X 100px."""
    charity_website: str
    """A URL to the charity’s website."""
    current_amount: Amount
    """Contains the current amount of donations that the campaign has received."""
    target_amount: Amount
    """Contains the campaign’s target fundraising goal."""
    started_at: datetime
    """The timestamp of when the broadcaster started the campaign."""


class CharityCampaignProgressData(TwitchObject):
    id: str
    """An ID that identifies the charity campaign."""
    broadcaster_id: str
    """An ID that identifies the broadcaster that’s running the campaign."""
    broadcaster_login: str
    """The broadcaster’s login name."""
    broadcaster_name: str
    """The broadcaster’s display name."""
    charity_name: str
    """The charity’s name."""
    charity_description: str
    """A description of the charity."""
    charity_logo: str
    """A URL to an image of the charity’s logo. The image’s type is PNG and its size is 100px X 100px."""
    charity_website: str
    """A URL to the charity’s website."""
    current_amount: Amount
    """Contains the current amount of donations that the campaign has received."""
    target_amount: Amount
    """Contains the campaign’s target fundraising goal."""


class CharityCampaignStopData(TwitchObject):
    id: str
    """An ID that identifies the charity campaign."""
    broadcaster_id: str
    """An ID that identifies the broadcaster that ran the campaign."""
    broadcaster_login: str
    """The broadcaster’s login name."""
    broadcaster_name: str
    """The broadcaster’s display name."""
    charity_name: str
    """The charity’s name."""
    charity_description: str
    """A description of the charity."""
    charity_logo: str
    """A URL to an image of the charity’s logo. The image’s type is PNG and its size is 100px X 100px."""
    charity_website: str
    """A URL to the charity’s website."""
    current_amount: Amount
    """Contains the final amount of donations that the campaign received."""
    target_amount: Amount
    """Contains the campaign’s target fundraising goal."""
    stopped_at: datetime
    """The timestamp of when the broadcaster stopped the campaign."""


class CharityDonationData(TwitchObject):
    id: str
    """An ID that identifies the donation. The ID is unique across campaigns."""
    campaign_id: str
    """An ID that identifies the charity campaign."""
    broadcaster_id: str
    """An ID that identifies the broadcaster that’s running the campaign."""
    broadcaster_login: str
    """The broadcaster’s login name."""
    broadcaster_name: str
    """The broadcaster’s display name."""
    user_id: str
    """An ID that identifies the user that donated to the campaign."""
    user_login: str
    """The user’s login name."""
    user_name: str
    """The user’s display name."""
    charity_name: str
    """The charity’s name."""
    charity_description: str
    """A description of the charity."""
    charity_logo: str
    """A URL to an image of the charity’s logo. The image’s type is PNG and its size is 100px X 100px."""
    charity_website: str
    """A URL to the charity’s website."""
    amount: Amount
    """Contains the amount of money that the user donated."""


class ChannelShoutoutCreateData(TwitchObject):
    broadcaster_user_id: str
    """An ID that identifies the broadcaster that sent the Shoutout."""
    broadcaster_user_login: str
    """The broadcaster’s login name."""
    broadcaster_user_name: str
    """The broadcaster’s display name."""
    to_broadcaster_user_id: str
    """An ID that identifies the broadcaster that received the Shoutout."""
    to_broadcaster_user_login: str
    """The broadcaster’s login name."""
    to_broadcaster_user_name: str
    """The broadcaster’s display name."""
    moderator_user_id: str
    """An ID that identifies the moderator that sent the Shoutout. If the broadcaster sent the Shoutout, this ID is the same as the ID in 
    broadcaster_user_id."""
    moderator_user_login: str
    """The moderator’s login name."""
    moderator_user_name: str
    """The moderator’s display name."""
    viewer_count: int
    """The number of users that were watching the broadcaster’s stream at the time of the Shoutout."""
    started_at: datetime
    """The timestamp of when the moderator sent the Shoutout."""
    cooldown_ends_at: datetime
    """The timestamp of when the broadcaster may send a Shoutout to a different broadcaster."""
    target_cooldown_ends_at: datetime
    """The timestamp of when the broadcaster may send another Shoutout to the broadcaster in to_broadcaster_user_id."""


class ChannelShoutoutReceiveData(TwitchObject):
    broadcaster_user_id: str
    """An ID that identifies the broadcaster that received the Shoutout."""
    broadcaster_user_login: str
    """The broadcaster’s login name."""
    broadcaster_user_name: str
    """The broadcaster’s display name."""
    from_broadcaster_user_id: str
    """An ID that identifies the broadcaster that sent the Shoutout."""
    from_broadcaster_user_login: str
    """The broadcaster’s login name."""
    from_broadcaster_user_name: str
    """The broadcaster’s display name."""
    viewer_count: int
    """The number of users that were watching the from-broadcaster’s stream at the time of the Shoutout."""
    started_at: datetime
    """The timestamp of when the moderator sent the Shoutout."""


class ChannelChatClearData(TwitchObject):
    broadcaster_user_id: str
    """The broadcaster user ID."""
    broadcaster_user_name: str
    """The broadcaster display name."""
    broadcaster_user_login: str
    """The broadcaster login."""


# Events

class ChannelPollBeginEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPollBeginData


class ChannelUpdateEvent(TwitchObject):
    subscription: Subscription
    event: ChannelUpdateData


class ChannelFollowEvent(TwitchObject):
    subscription: Subscription
    event: ChannelFollowData


class ChannelSubscribeEvent(TwitchObject):
    subscription: Subscription
    event: ChannelSubscribeData


class ChannelSubscriptionEndEvent(TwitchObject):
    subscription: Subscription
    event: ChannelSubscribeData


class ChannelSubscriptionGiftEvent(TwitchObject):
    subscription: Subscription
    event: ChannelSubscriptionGiftData


class ChannelSubscriptionMessageEvent(TwitchObject):
    subscription: Subscription
    event: ChannelSubscriptionMessageData


class ChannelCheerEvent(TwitchObject):
    subscription: Subscription
    event: ChannelCheerData


class ChannelRaidEvent(TwitchObject):
    subscription: Subscription
    event: ChannelRaidData


class ChannelBanEvent(TwitchObject):
    subscription: Subscription
    event: ChannelBanData


class ChannelUnbanEvent(TwitchObject):
    subscription: Subscription
    event: ChannelUnbanData


class ChannelModeratorAddEvent(TwitchObject):
    subscription: Subscription
    event: ChannelModeratorAddData


class ChannelModeratorRemoveEvent(TwitchObject):
    subscription: Subscription
    event: ChannelModeratorRemoveData


class ChannelPointsCustomRewardAddEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPointsCustomRewardData


class ChannelPointsCustomRewardUpdateEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPointsCustomRewardData


class ChannelPointsCustomRewardRemoveEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPointsCustomRewardData


class ChannelPointsCustomRewardRedemptionAddEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPointsCustomRewardRedemptionData


class ChannelPointsCustomRewardRedemptionUpdateEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPointsCustomRewardRedemptionData


class ChannelPollProgressEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPollProgressData


class ChannelPollEndEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPollEndData


class ChannelPredictionEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPredictionData


class ChannelPredictionEndEvent(TwitchObject):
    subscription: Subscription
    event: ChannelPredictionEndData


class DropEntitlementGrantEvent(TwitchObject):
    subscription: Subscription
    event: DropEntitlementGrantData


class ExtensionBitsTransactionCreateEvent(TwitchObject):
    subscription: Subscription
    event: ExtensionBitsTransactionCreateData


class GoalEvent(TwitchObject):
    subscription: Subscription
    event: GoalData


class HypeTrainEvent(TwitchObject):
    subscription: Subscription
    event: HypeTrainData


class HypeTrainEndEvent(TwitchObject):
    subscription: Subscription
    event: HypeTrainEndData


class StreamOnlineEvent(TwitchObject):
    subscription: Subscription
    event: StreamOnlineData


class StreamOfflineEvent(TwitchObject):
    subscription: Subscription
    event: StreamOfflineData


class UserAuthorizationGrantEvent(TwitchObject):
    subscription: Subscription
    event: UserAuthorizationGrantData


class UserAuthorizationRevokeEvent(TwitchObject):
    subscription: Subscription
    event: UserAuthorizationRevokeData


class UserUpdateEvent(TwitchObject):
    subscription: Subscription
    event: UserUpdateData


class ShieldModeEvent(TwitchObject):
    subscription: Subscription
    event: ShieldModeData


class CharityCampaignStartEvent(TwitchObject):
    subscription: Subscription
    event: CharityCampaignStartData


class CharityCampaignProgressEvent(TwitchObject):
    subscription: Subscription
    event: CharityCampaignProgressData


class CharityCampaignStopEvent(TwitchObject):
    subscription: Subscription
    event: CharityCampaignStopData


class CharityDonationEvent(TwitchObject):
    subscription: Subscription
    event: CharityDonationData


class ChannelShoutoutCreateEvent(TwitchObject):
    subscription: Subscription
    event: ChannelShoutoutCreateData


class ChannelShoutoutReceiveEvent(TwitchObject):
    subscription: Subscription
    event: ChannelShoutoutReceiveData

class ChannelChatClearEvent(TwitchObject):
    subscription: Subscription
    event: ChannelChatClearData
