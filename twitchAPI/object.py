#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
from datetime import datetime
from enum import Enum
from typing import Optional, get_type_hints, Union, List, Dict
from dateutil import parser as du_parser

from twitchAPI.types import StatusCode, VideoType, HypeTrainContributionMethod, DropsEntitlementFulfillmentStatus, CustomRewardRedemptionStatus,\
    PollStatus, PredictionStatus


class TwitchObject:
    @staticmethod
    def _val_by_instance(instance, val):
        if val is None:
            return None
        origin = instance.__origin__ if hasattr(instance, '__origin__') else None
        if instance == datetime:
            return du_parser.isoparse(val) if len(val) > 0 else None
        elif origin == list:
            c = instance.__args__[0]
            return [TwitchObject._val_by_instance(c, x) for x in val]
        elif origin == dict:
            c1 = instance.__args__[0]
            c2 = instance.__args__[1]
            return {TwitchObject._val_by_instance(c1, x1): TwitchObject._val_by_instance(c2, x2) for x1, x2 in val.items()}
        elif origin == Union:
            # TODO: only works for optional pattern, fix to try out all possible patterns?
            c1 = instance.__args__[0]
            print(c1)
            print(val)
            return TwitchObject._val_by_instance(c1, val)
        elif issubclass(instance, TwitchObject):
            return instance(**val)
        else:
            return instance(val)

    @staticmethod
    def _dict_val_by_instance(instance, val, include_none_values):
        if val is None:
            return None
        origin = instance.__origin__ if hasattr(instance, '__origin__') else None
        if instance == datetime:
            return val.isoformat() if val is not None else None
        elif origin == list:
            c = instance.__args__[0]
            return [TwitchObject._dict_val_by_instance(c, x, include_none_values) for x in val]
        elif origin == dict:
            c1 = instance.__args__[0]
            c2 = instance.__args__[1]
            return {TwitchObject._dict_val_by_instance(c1, x1, include_none_values):
                    TwitchObject._dict_val_by_instance(c2, x2, include_none_values) for x1, x2 in val.items()}
        elif origin == Union:
            # TODO: only works for optional pattern, fix to try out all possible patterns?
            c1 = instance.__args__[0]
            return TwitchObject._dict_val_by_instance(c1, val, include_none_values)
        elif issubclass(instance, TwitchObject):
            return val.to_dict(include_none_values)
        elif isinstance(val, Enum):
            return val.value
        return instance(val)

    @classmethod
    def _get_annotations(cls):
        d = {}
        for c in cls.mro():
            try:
                d.update(**c.__annotations__)
            except AttributeError:
                pass
        return d

    def to_dict(self, include_none_values: bool = False) -> dict:
        """build dict based on annotation types"""
        d = {}
        annotations = self._get_annotations()
        for name, val in self.__dict__.items():
            val = None
            cls = annotations.get(name)
            try:
                val = getattr(self, name)
            except AttributeError:
                pass
            if val is None and not include_none_values:
                continue
            d[name] = TwitchObject._dict_val_by_instance(cls, val, include_none_values)
        return d

    def __init__(self, **kwargs):
        merged_annotations = self._get_annotations()
        for name, cls in merged_annotations.items():
            if name not in kwargs.keys():
                continue
            self.__setattr__(name, TwitchObject._val_by_instance(cls, kwargs.get(name)))


class IterTwitchObject(TwitchObject):

    def __iter__(self):
        if not hasattr(self, 'data') or not isinstance(self.__getattribute__('data'), list):
            raise ValueError('Object is missing data attribute of type list')
        for i in self.__getattribute__('data'):
            yield i


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
    to_name: str
    followed_at: datetime


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


class CodeStatus(TwitchObject):
    code: str
    status: StatusCode


class Game(TwitchObject):
    box_art_url: str
    id: str
    name: str


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


class BroadcasterSubscriptions(IterTwitchObject):
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


class ChannelTeam(TwitchObject):
    broadcaster_id: str
    broadcaster_name: str
    broadcaster_login: str
    background_image_url: str
    banner: str
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


class SearchChannelResult(ChannelInformation):
    is_live: bool
    tags_ids: List[str]
    started_at: datetime


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
    image: str
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
    bits_votes: int


class Poll(TwitchObject):
    id: str
    broadcaster_name: str
    broadcaster_id: str
    broadcaster_login: str
    title: str
    choices: List[PollChoice]
    bits_voting_enabled: bool
    bits_per_vote: int
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


class ChatBadge(TwitchObject):
    set_id: str
    versions: List[ChatBadgeVersion]
