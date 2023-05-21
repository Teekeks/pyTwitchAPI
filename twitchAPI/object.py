#  Copyright (c) 2022. Lena "Teekeks" During <info@teawork.de>
"""
Objects used by the Twitch API
------------------------------
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Union, List, Dict, Generic, TypeVar

from aiohttp import ClientSession
from dateutil import parser as du_parser

from twitchAPI.helper import build_url
from twitchAPI.types import StatusCode, VideoType, HypeTrainContributionMethod, DropsEntitlementFulfillmentStatus, CustomRewardRedemptionStatus, \
    PollStatus, PredictionStatus, SoundtrackSourceType

T = TypeVar('T')

__all__ = ['TwitchObject', 'IterTwitchObject', 'AsyncIterTwitchObject', 'TwitchUser', 'TwitchUserFollow', 'TwitchUserFollowResult', 'DateRange',
           'ExtensionAnalytic', 'GameAnalytics', 'CreatorGoal', 'BitsLeaderboardEntry', 'BitsLeaderboard', 'ProductCost', 'ProductData',
           'ExtensionTransaction', 'ChatSettings', 'CreatedClip', 'Clip', 'CodeStatus', 'Game', 'AutoModStatus', 'BannedUser', 'BanUserResponse',
           'BlockedTerm', 'Moderator', 'CreateStreamMarkerResponse', 'Stream', 'StreamMarker', 'StreamMarkers', 'GetStreamMarkerResponse',
           'BroadcasterSubscription', 'BroadcasterSubscriptions', 'UserSubscription', 'StreamTag', 'TeamUser', 'ChannelTeam', 'UserExtension',
           'ActiveUserExtension', 'UserActiveExtensions', 'VideoMutedSegments', 'Video', 'ChannelInformation', 'SearchChannelResult',
           'SearchCategoryResult', 'StartCommercialResult', 'Cheermote', 'GetCheermotesResponse', 'HypeTrainContribution', 'HypeTrainEventData',
           'HypeTrainEvent', 'DropsEntitlement', 'MaxPerStreamSetting', 'MaxPerUserPerStreamSetting', 'GlobalCooldownSetting', 'CustomReward',
           'PartialCustomReward', 'CustomRewardRedemption', 'ChannelEditor', 'BlockListEntry', 'PollChoice', 'Poll', 'Predictor', 'PredictionOutcome',
           'Prediction', 'RaidStartResult', 'ChatBadgeVersion', 'ChatBadge', 'Emote', 'GetEmotesResponse', 'EventSubSubscription',
           'GetEventSubSubscriptionResult', 'StreamCategory', 'ChannelStreamScheduleSegment', 'StreamVacation', 'ChannelStreamSchedule',
           'ChannelVIP', 'UserChatColor', 'Artist', 'Album', 'Soundtrack', 'TrackSource', 'CurrentSoundtrack', 'Playlist', 'Chatter',
           'GetChattersResponse', 'ShieldModeStatus', 'CharityAmount', 'CharityCampaign', 'CharityCampaignDonation', 'AutoModSettings',
           'ChannelFollower', 'ChannelFollowersResult', 'FollowedChannel', 'FollowedChannelsResult']


class TwitchObject:
    """
    A lot of API calls return a child of this in some way (either directly or via generator).
    You can always use the :const:`~twitchAPI.object.TwitchObject.to_dict()` method to turn that object to a dictionary.

    Example:

    .. code-block:: python

        blocked_term = await twitch.add_blocked_term('broadcaster_id', 'moderator_id', 'bad_word')
        print(blocked_term.id)"""
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
            return TwitchObject._val_by_instance(c1, val)
        elif issubclass(instance, TwitchObject):
            return instance(**val)
        else:
            return instance(val)

    @staticmethod
    def _dict_val_by_instance(instance, val, include_none_values):
        if val is None:
            return None
        if instance is None:
            return val
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
        """build dict based on annotation types

        :param include_none_values: if fields that have None values should be included in the dictionary
        """
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
            if name[0] == '_':
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
    """Special type of :const:`~twitchAPI.object.TwitchObject`.
       These usually have some list inside that you may want to dicrectly itterate over in your API usage but that also contain other usefull data
       outside of that List.

       Example:

       .. code-block:: python

          lb = await twitch.get_bits_leaderboard()
          print(lb.total)
          for e in lb:
              print(f'#{e.rank:02d} - {e.user_name}: {e.score}')"""

    def __iter__(self):
        if not hasattr(self, 'data') or not isinstance(self.__getattribute__('data'), list):
            raise ValueError('Object is missing data attribute of type list')
        for i in self.__getattribute__('data'):
            yield i


class AsyncIterTwitchObject(TwitchObject, Generic[T]):
    """A few API calls will have usefull data outside of the list the pagination itterates over.
       For those cases, this object exist.

       Example:

       .. code-block:: python

           schedule = await twitch.get_channel_stream_schedule('user_id')
           print(schedule.broadcaster_name)
           async for segment in schedule:
               print(segment.title)"""

    def __init__(self, _data, **kwargs):
        super(AsyncIterTwitchObject, self).__init__(**kwargs)
        self.__idx = 0
        self._data = _data

    def __aiter__(self):
        return self

    async def __anext__(self) -> T:
        if not hasattr(self, self._data['iter_field']) or not isinstance(self.__getattribute__(self._data['iter_field']), list):
            raise ValueError(f'Object is missing {self._data["iter_field"]} attribute of type list')
        data = self.__getattribute__(self._data['iter_field'])
        if len(data) > self.__idx:
            self.__idx += 1
            return data[self.__idx - 1]
        # make request
        if self._data['param']['after'] is None:
            raise StopAsyncIteration()
        _url = build_url(self._data['url'], self._data['param'], remove_none=True, split_lists=self._data['split'])
        async with ClientSession() as session:
            response = await self._data['req'](session, _url, self._data['auth_t'], self._data['auth_s'], self._data['body'])
            _data = await response.json()
        _after = _data.get('pagination', {}).get('cursor')
        self._data['param']['after'] = _after
        if self._data['in_data']:
            _data = _data['data']
        # refill data
        merged_annotations = self._get_annotations()
        for name, cls in merged_annotations.items():
            if name not in _data.keys():
                continue
            self.__setattr__(name, TwitchObject._val_by_instance(cls, _data.get(name)))
        data = self.__getattribute__(self._data['iter_field'])
        self.__idx = 1
        if len(data) == 0:
            raise StopAsyncIteration()
        return data[self.__idx - 1]


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


class Artist(TwitchObject):
    id: str
    name: str
    creator_channel_id: str


class Album(TwitchObject):
    id: str
    name: str
    image_url: str


class Soundtrack(TwitchObject):
    artists: List[Artist]
    id: str
    isrc: str
    duration: int
    title: str
    album: Album


class TrackSource(TwitchObject):
    content_type: SoundtrackSourceType
    id: str
    image_url: str
    soundtrack_url: str
    spotify_url: str
    title: str


class CurrentSoundtrack(TwitchObject):
    track: Soundtrack
    source: TrackSource


class Playlist(TwitchObject):
    title: str
    id: str
    image_url: str
    description: str


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
