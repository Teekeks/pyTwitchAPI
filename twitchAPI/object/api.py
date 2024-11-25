#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
"""
Objects used by the Twitch API
------------------------------
"""

from datetime import datetime
from typing import Optional, List, Dict

from twitchAPI.object.base import TwitchObject, IterTwitchObject, AsyncIterTwitchObject
from twitchAPI.type import StatusCode, VideoType, HypeTrainContributionMethod, DropsEntitlementFulfillmentStatus, CustomRewardRedemptionStatus, \
    PollStatus, PredictionStatus


__all__ = ['TwitchUser', 'TwitchUserFollow', 'TwitchUserFollowResult', 'DateRange',
           'ExtensionAnalytic', 'GameAnalytics', 'CreatorGoal', 'BitsLeaderboardEntry', 'BitsLeaderboard', 'ProductCost', 'ProductData',
           'ExtensionTransaction', 'ChatSettings', 'CreatedClip', 'Clip', 'CodeStatus', 'Game', 'AutoModStatus', 'BannedUser', 'BanUserResponse',
           'BlockedTerm', 'Moderator', 'CreateStreamMarkerResponse', 'Stream', 'StreamMarker', 'StreamMarkers', 'GetStreamMarkerResponse',
           'BroadcasterSubscription', 'BroadcasterSubscriptions', 'UserSubscription', 'StreamTag', 'TeamUser', 'ChannelTeam', 'UserExtension',
           'ActiveUserExtension', 'UserActiveExtensions', 'VideoMutedSegments', 'Video', 'ChannelInformation', 'SearchChannelResult',
           'SearchCategoryResult', 'StartCommercialResult', 'Cheermote', 'GetCheermotesResponse', 'HypeTrainContribution', 'HypeTrainEventData',
           'HypeTrainEvent', 'DropsEntitlement', 'MaxPerStreamSetting', 'MaxPerUserPerStreamSetting', 'GlobalCooldownSetting', 'CustomReward',
           'PartialCustomReward', 'CustomRewardRedemption', 'ChannelEditor', 'BlockListEntry', 'PollChoice', 'Poll', 'Predictor', 'PredictionOutcome',
           'Prediction', 'RaidStartResult', 'ChatBadgeVersion', 'ChatBadge', 'Emote', 'UserEmote', 'GetEmotesResponse', 'EventSubSubscription',
           'GetEventSubSubscriptionResult', 'StreamCategory', 'ChannelStreamScheduleSegment', 'StreamVacation', 'ChannelStreamSchedule',
           'ChannelVIP', 'UserChatColor', 'Chatter', 'GetChattersResponse', 'ShieldModeStatus', 'CharityAmount', 'CharityCampaign',
           'CharityCampaignDonation', 'AutoModSettings', 'ChannelFollower', 'ChannelFollowersResult', 'FollowedChannel', 'FollowedChannelsResult',
           'ContentClassificationLabel', 'AdSchedule', 'AdSnoozeResponse', 'SendMessageResponse', 'ChannelModerator', 'UserEmotesResponse',
           'WarnResponse', 'SharedChatParticipant', 'SharedChatSession']


class TwitchUser(TwitchObject):
    id: str
    login: str
    display_name: str
    type: str
    broadcaster_type: str
    description: str
    profile_image_url: str
    offline_image_url: str
    view_count: int
    email: str = None
    created_at: datetime


class TwitchUserFollow(TwitchObject):
    from_id: str
    from_login: str
    from_name: str
    to_id: str
    to_login: str
    to_name: str
    followed_at: datetime


class TwitchUserFollowResult(AsyncIterTwitchObject[TwitchUserFollow]):
    total: int
    data: List[TwitchUserFollow]


class ChannelFollower(TwitchObject):
    followed_at: datetime
    user_id: str
    user_name: str
    user_login: str


class ChannelFollowersResult(AsyncIterTwitchObject[ChannelFollower]):
    total: int
    data: List[ChannelFollower]


class FollowedChannel(TwitchObject):
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str
    followed_at: datetime


class FollowedChannelsResult(AsyncIterTwitchObject[FollowedChannel]):
    total: int
    data: List[FollowedChannel]


class DateRange(TwitchObject):
    ended_at: datetime
    started_at: datetime


class ExtensionAnalytic(TwitchObject):
    extension_id: str
    URL: str
    type: str
    date_range: DateRange


class GameAnalytics(TwitchObject):
    game_id: str
    URL: str
    type: str
    date_range: DateRange


class CreatorGoal(TwitchObject):
    id: str
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    type: str
    description: str
    current_amount: int
    target_amount: int
    created_at: datetime


class BitsLeaderboardEntry(TwitchObject):
    user_id: str
    user_login: str
    user_name: str
    rank: int
    score: int


class BitsLeaderboard(IterTwitchObject):
    data: List[BitsLeaderboardEntry]
    date_range: DateRange
    total: int


class ProductCost(TwitchObject):
    amount: int
    type: str


class ProductData(TwitchObject):
    domain: str
    sku: str
    cost: ProductCost


class ExtensionTransaction(TwitchObject):
    id: str
    timestamp: datetime
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str
    user_id: str
    user_login: str
    user_name: str
    product_type: str
    product_data: ProductData
    inDevelopment: bool
    displayName: str
    expiration: str
    broadcast: str


class ChatSettings(TwitchObject):
    broadcaster_id: str
    moderator_id: str
    emote_mode: bool
    slow_mode: bool
    slow_mode_wait_time: int
    follower_mode: bool
    follower_mode_duration: int
    subscriber_mode: bool
    unique_chat_mode: bool
    non_moderator_chat_delay: bool
    non_moderator_chat_delay_duration: int


class CreatedClip(TwitchObject):
    id: str
    edit_url: str


class Clip(TwitchObject):
    id: str
    url: str
    embed_url: str
    broadcaster_id: str
    broadcaster_name: str
    creator_id: str
    creator_name: str
    video_id: str
    game_id: str
    language: str
    title: str
    view_count: int
    created_at: datetime
    thumbnail_url: str
    duration: float
    vod_offset: int
    is_featured: bool


class CodeStatus(TwitchObject):
    code: str
    status: StatusCode


class Game(TwitchObject):
    box_art_url: str
    id: str
    name: str
    igdb_id: str


class AutoModStatus(TwitchObject):
    msg_id: str
    is_permitted: bool


class BannedUser(TwitchObject):
    user_id: str
    user_login: str
    user_name: str
    expires_at: datetime
    created_at: datetime
    reason: str
    moderator_id: str
    moderator_login: str
    moderator_name: str


class BanUserResponse(TwitchObject):
    broadcaster_id: str
    moderator_id: str
    user_id: str
    created_at: datetime
    end_time: datetime


class BlockedTerm(TwitchObject):
    broadcaster_id: str
    moderator_id: str
    id: str
    text: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class Moderator(TwitchObject):
    user_id: str
    user_login: str
    user_name: str


class CreateStreamMarkerResponse(TwitchObject):
    id: str
    created_at: datetime
    description: str
    position_seconds: int


class Stream(TwitchObject):
    id: str
    user_id: str
    user_login: str
    user_name: str
    game_id: str
    game_name: str
    type: str
    title: str
    viewer_count: int
    started_at: datetime
    language: str
    thumbnail_url: str
    tag_ids: List[str]
    is_mature: bool
    tags: List[str]


class StreamMarker(TwitchObject):
    id: str
    created_at: datetime
    description: str
    position_seconds: int
    URL: str


class StreamMarkers(TwitchObject):
    video_id: str
    markers: List[StreamMarker]


class GetStreamMarkerResponse(TwitchObject):
    user_id: str
    user_name: str
    user_login: str
    videos: List[StreamMarkers]


class BroadcasterSubscription(TwitchObject):
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str
    gifter_id: str
    gifter_login: str
    gifter_name: str
    is_gift: bool
    tier: str
    plan_name: str
    user_id: str
    user_name: str
    user_login: str


class BroadcasterSubscriptions(AsyncIterTwitchObject[BroadcasterSubscription]):
    total: int
    points: int
    data: List[BroadcasterSubscription]


class UserSubscription(TwitchObject):
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    is_gift: bool
    tier: str


class StreamTag(TwitchObject):
    tag_id: str
    is_auto: bool
    localization_names: Dict[str, str]
    localization_descriptions: Dict[str, str]


class TeamUser(TwitchObject):
    user_id: str
    user_name: str
    user_login: str


class ChannelTeam(TwitchObject):
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    background_image_url: str
    banner: str
    users: Optional[List[TeamUser]]
    created_at: datetime
    updated_at: datetime
    info: str
    thumbnail_url: str
    team_name: str
    team_display_name: str
    id: str


class UserExtension(TwitchObject):
    id: str
    version: str
    can_activate: bool
    type: List[str]
    name: str


class ActiveUserExtension(UserExtension):
    x: int
    y: int
    active: bool


class UserActiveExtensions(TwitchObject):
    panel: Dict[str, ActiveUserExtension]
    overlay: Dict[str, ActiveUserExtension]
    component: Dict[str, ActiveUserExtension]


class VideoMutedSegments(TwitchObject):
    duration: int
    offset: int


class Video(TwitchObject):
    id: str
    stream_id: str
    user_id: str
    user_login: str
    user_name: str
    title: str
    description: str
    created_at: datetime
    published_at: datetime
    url: str
    thumbnail_url: str
    viewable: str
    view_count: int
    language: str
    type: VideoType
    duration: str
    muted_segments: List[VideoMutedSegments]


class ChannelInformation(TwitchObject):
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str
    game_name: str
    game_id: str
    broadcaster_language: str
    title: str
    delay: int
    tags: List[str]
    content_classification_labels: List[str]
    is_branded_content: bool


class SearchChannelResult(TwitchObject):
    broadcaster_language: str
    """The ISO 639-1 two-letter language code of the language used by the broadcaster. For example, en for English. 
    If the broadcaster uses a language not in the list of supported stream languages, the value is other."""
    broadcaster_login: str
    """The broadcaster’s login name."""
    display_name: str
    """The broadcaster’s display name."""
    game_id: str
    """The ID of the game that the broadcaster is playing or last played."""
    game_name: str
    """The name of the game that the broadcaster is playing or last played."""
    id: str
    """An ID that uniquely identifies the channel (this is the broadcaster’s ID)."""
    is_live: bool
    """A Boolean value that determines whether the broadcaster is streaming live. Is True if the broadcaster is streaming live; otherwise, False."""
    tags: List[str]
    """The tags applied to the channel."""
    thumbnail_url: str
    """A URL to a thumbnail of the broadcaster’s profile image."""
    title: str
    """The stream’s title. Is an empty string if the broadcaster didn’t set it."""
    started_at: Optional[datetime]
    """The datetime of when the broadcaster started streaming. None if the broadcaster is not streaming live."""


class SearchCategoryResult(TwitchObject):
    id: str
    name: str
    box_art_url: str


class StartCommercialResult(TwitchObject):
    length: int
    message: str
    retry_after: int


class Cheermote(TwitchObject):
    min_bits: int
    id: str
    color: str
    images: Dict[str, Dict[str, Dict[str, str]]]
    can_cheer: bool
    show_in_bits_card: bool


class GetCheermotesResponse(TwitchObject):
    prefix: str
    tiers: List[Cheermote]
    type: str
    order: int
    last_updated: datetime
    is_charitable: bool


class HypeTrainContribution(TwitchObject):
    total: int
    type: HypeTrainContributionMethod
    user: str


class HypeTrainEventData(TwitchObject):
    broadcaster_id: str
    cooldown_end_time: datetime
    expires_at: datetime
    goal: int
    id: str
    last_contribution: HypeTrainContribution
    level: int
    started_at: datetime
    top_contributions: List[HypeTrainContribution]
    total: int


class HypeTrainEvent(TwitchObject):
    id: str
    event_type: str
    event_timestamp: datetime
    version: str
    event_data: HypeTrainEventData


class DropsEntitlement(TwitchObject):
    id: str
    benefit_id: str
    timestamp: datetime
    user_id: str
    game_id: str
    fulfillment_status: DropsEntitlementFulfillmentStatus
    updated_at: datetime


class MaxPerStreamSetting(TwitchObject):
    is_enabled: bool
    max_per_stream: int


class MaxPerUserPerStreamSetting(TwitchObject):
    is_enabled: bool
    max_per_user_per_stream: int


class GlobalCooldownSetting(TwitchObject):
    is_enabled: bool
    global_cooldown_seconds: int


class CustomReward(TwitchObject):
    broadcaster_name: str
    broadcaster_login: str
    broadcaster_id: str
    id: str
    image: Dict[str, str]
    background_color: str
    is_enabled: bool
    cost: int
    title: str
    prompt: str
    is_user_input_required: bool
    max_per_stream_setting: MaxPerStreamSetting
    max_per_user_per_stream_setting: MaxPerUserPerStreamSetting
    global_cooldown_setting: GlobalCooldownSetting
    is_paused: bool
    is_in_stock: bool
    default_image: Dict[str, str]
    should_redemptions_skip_request_queue: bool
    redemptions_redeemed_current_stream: int
    cooldown_expires_at: datetime


class PartialCustomReward(TwitchObject):
    id: str
    title: str
    prompt: str
    cost: int


class CustomRewardRedemption(TwitchObject):
    broadcaster_name: str
    broadcaster_login: str
    broadcaster_id: str
    id: str
    user_id: str
    user_name: str
    user_input: str
    status: CustomRewardRedemptionStatus
    redeemed_at: datetime
    reward: PartialCustomReward


class ChannelEditor(TwitchObject):
    user_id: str
    user_name: str
    created_at: datetime


class BlockListEntry(TwitchObject):
    user_id: str
    user_login: str
    user_name: str


class PollChoice(TwitchObject):
    id: str
    title: str
    votes: int
    channel_point_votes: int


class Poll(TwitchObject):
    id: str
    broadcaster_name: str
    broadcaster_id: str
    broadcaster_login: str
    title: str
    choices: List[PollChoice]
    channel_point_voting_enabled: bool
    channel_points_per_vote: int
    status: PollStatus
    duration: int
    started_at: datetime


class Predictor(TwitchObject):
    user_id: str
    user_name: str
    user_login: str
    channel_points_used: int
    channel_points_won: int


class PredictionOutcome(TwitchObject):
    id: str
    title: str
    users: int
    channel_points: int
    top_predictors: Optional[List[Predictor]]
    color: str


class Prediction(TwitchObject):
    id: str
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    title: str
    winning_outcome_id: Optional[str]
    outcomes: List[PredictionOutcome]
    prediction_window: int
    status: PredictionStatus
    created_at: datetime
    ended_at: Optional[datetime]
    locked_at: Optional[datetime]


class RaidStartResult(TwitchObject):
    created_at: datetime
    is_mature: bool


class ChatBadgeVersion(TwitchObject):
    id: str
    image_url_1x: str
    image_url_2x: str
    image_url_4x: str
    title: str
    description: str
    click_action: Optional[str]
    click_url: Optional[str]


class ChatBadge(TwitchObject):
    set_id: str
    versions: List[ChatBadgeVersion]


class Emote(TwitchObject):
    id: str
    name: str
    images: Dict[str, str]
    tier: str
    emote_type: str
    emote_set_id: str
    format: List[str]
    scale: List[str]
    theme_mode: List[str]


class UserEmote(Emote):
    owner_id: str


class GetEmotesResponse(IterTwitchObject):
    data: List[Emote]
    template: str


class EventSubSubscription(TwitchObject):
    id: str
    status: str
    type: str
    version: str
    condition: Dict[str, str]
    created_at: datetime
    transport: Dict[str, str]
    cost: int


class GetEventSubSubscriptionResult(AsyncIterTwitchObject[EventSubSubscription]):
    total: int
    total_cost: int
    max_total_cost: int
    data: List[EventSubSubscription]


class StreamCategory(TwitchObject):
    id: str
    name: str


class ChannelStreamScheduleSegment(TwitchObject):
    id: str
    start_time: datetime
    end_time: datetime
    title: str
    canceled_until: Optional[datetime]
    category: StreamCategory
    is_recurring: bool


class StreamVacation(TwitchObject):
    start_time: datetime
    end_time: datetime


class ChannelStreamSchedule(AsyncIterTwitchObject[ChannelStreamScheduleSegment]):
    segments: List[ChannelStreamScheduleSegment]
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    vacation: Optional[StreamVacation]


class ChannelVIP(TwitchObject):
    user_id: str
    user_name: str
    user_login: str


class UserChatColor(TwitchObject):
    user_id: str
    user_name: str
    user_login: str
    color: str


class Chatter(TwitchObject):
    user_id: str
    user_login: str
    user_name: str


class GetChattersResponse(AsyncIterTwitchObject[Chatter]):
    data: List[Chatter]
    total: int


class ShieldModeStatus(TwitchObject):
    is_active: bool
    moderator_id: str
    moderator_login: str
    moderator_name: str
    last_activated_at: Optional[datetime]


class CharityAmount(TwitchObject):
    value: int
    decimal_places: int
    currency: str


class CharityCampaign(TwitchObject):
    id: str
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str
    charity_name: str
    charity_description: str
    charity_logo: str
    charity_website: str
    current_amount: CharityAmount
    target_amount: CharityAmount


class CharityCampaignDonation(TwitchObject):
    id: str
    campaign_id: str
    user_id: str
    user_name: str
    user_login: str
    amount: CharityAmount


class AutoModSettings(TwitchObject):
    broadcaster_id: str
    moderator_id: str
    overall_level: Optional[int]
    disability: int
    aggression: int
    sexuality_sex_or_gender: int
    misogyny: int
    bullying: int
    swearing: int
    race_ethnicity_or_religion: int
    sex_based_terms: int


class ContentClassificationLabel(TwitchObject):
    id: str
    description: str
    name: str


class AdSchedule(TwitchObject):
    snooze_count: int
    """The number of snoozes available for the broadcaster."""
    snooze_refresh_at: Optional[datetime]
    """The UTC timestamp when the broadcaster will gain an additional snooze."""
    next_ad_at: Optional[datetime]
    """The UTC timestamp of the broadcaster’s next scheduled ad. Empty if the channel has no ad scheduled or is not live."""
    duration: int
    """The length in seconds of the scheduled upcoming ad break."""
    last_ad_at: Optional[datetime]
    """The UTC timestamp of the broadcaster’s last ad-break. Empty if the channel has not run an ad or is not live."""
    preroll_free_time: int
    """The amount of pre-roll free time remaining for the channel in seconds. Returns 0 if they are currently not pre-roll free."""


class AdSnoozeResponse(TwitchObject):
    snooze_count: int
    """The number of snoozes available for the broadcaster."""
    snooze_refresh_at: Optional[datetime]
    """The UTC timestamp when the broadcaster will gain an additional snooze"""
    next_ad_at: Optional[datetime]
    """The UTC timestamp of the broadcaster’s next scheduled ad"""


class SendMessageDropReason(TwitchObject):
    code: str
    """Code for why the message was dropped."""
    message: str
    """Message for why the message was dropped."""


class SendMessageResponse(TwitchObject):
    message_id: str
    """The message id for the message that was sent."""
    is_sent: bool
    """If the message passed all checks and was sent."""
    drop_reason: Optional[SendMessageDropReason]
    """The reason the message was dropped, if any."""


class ChannelModerator(TwitchObject):
    broadcaster_id: str
    """An ID that uniquely identifies the channel this user can moderate."""
    broadcaster_login: str
    """The channel’s login name."""
    broadcaster_name: str
    """The channels’ display name."""


class UserEmotesResponse(AsyncIterTwitchObject):
    template: str
    """A templated URL. Uses the values from the id, format, scale, and theme_mode fields to replace the like-named placeholder strings in the 
    templated URL to create a CDN (content delivery network) URL that you use to fetch the emote."""
    data: List[UserEmote]


class WarnResponse(TwitchObject):
    broadcaster_id: str
    """The ID of the channel in which the warning will take effect."""
    user_id: str
    """The ID of the warned user."""
    moderator_id: str
    """The ID of the user who applied the warning."""
    reason: str
    """The reason provided for warning."""


class SharedChatParticipant(TwitchObject):
    broadcaster_id: str
    """The User ID of the participant channel."""


class SharedChatSession(TwitchObject):
    session_id: str
    """The unique identifier for the shared chat session."""
    host_broadcaster_id: str
    """The User ID of the host channel."""
    participants: List[SharedChatParticipant]
    """The list of participants in the session."""
    created_at: datetime
    """The UTC timestamp when the session was created."""
    updated_at: datetime
    """The UTC timestamp when the session was last updated."""
