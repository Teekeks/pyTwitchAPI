:orphan:

Changelog
=========

*************
Version 4.0.0
*************

.. note:: This Version introduces a lot of breaking changes. Please see the :doc:`v4-migration` to learn how to migrate.

Keystone Features
-----------------

- EventSub now supports the newly added Webhook transport
- EventSub is now using TwitchObject based callback payloads instead of raw dictionaries
- Chat now supports Command Middleware, check out :doc:`/tutorial/chat-use-middleware` for more info
- Added :const:`~twitchAPI.oauth.UserAuthenticationStorageHelper` to cut down on common boilerplate code, check out :doc:`/tutorial/reuse-user-token` for more info

Twitch
------

- Added new fields :const:`~twitchAPI.object.api.ChannelInformation.is_branded_content` and :const:`~twitchAPI.object.api.ChannelInformation.content_classification_labels` to response of :const:`~twitchAPI.twitch.Twitch.get_channel_information()`
- Added new parameters :paramref:`~twitchAPI.twitch.Twitch.modify_channel_information.is_branded_content` and :paramref:`~twitchAPI.twitch.Twitch.modify_channel_information.content_classification_labels` to :const:`~twitchAPI.twitch.Twitch.modify_channel_information()`
- Added new Endpoint "Get Content Classification Labels" :const:`~twitchAPI.twitch.Twitch.get_content_classification_labels()`

- Removed the following deprecated Endpoints:

  - "Get Soundstrack Current Track"
  - "Get SoundTrack Playlist"
  - "Get Soundtrack Playlists"

- :const:`~twitchAPI.twitch.Twitch.get_polls()` now allows up to 20 poll IDs

EventSub
--------

- Moved old EventSub from :const:`twitchAPI.eventsub` to new package :const:`twitchAPI.eventsub.webhook` and renamed it to :const:`~twitchAPI.eventsub.webhook.EventSubWebhook`
- Added new EventSub Websocket transport :const:`~twitchAPI.eventsub.websocket.EventSubWebsocket`
- All EventSub callbacks now use :const:`~twitchAPI.object.base.TwitchObject` based Payloads instead of raw dictionaries. See :ref:`eventsub-available-topics` for a list of all available Payloads
- Added :const:`~twitchAPI.eventsub.base.EventSubBase.listen_channel_update_v2()`
- Added option for :const:`~twitchAPI.eventsub.webhook.EventSubWebhook` to specify a asyncio loop via :paramref:`~twitchAPI.eventsub.webhook.EventSubWebhook.callback_loop` in which to run all callbacks in
- Added option for :const:`~twitchAPI.eventsub.websocket.EventSubWebsocket` to specify a asyncio loop via :paramref:`~twitchAPI.eventsub.websocket.EventSubWebsocket.callback_loop` in which to run all callbacks in
- Added automatical removal of tailing ``/`` in :paramref:`~twitchAPI.eventsub.webhook.EventSubWebhook.callback_url` if present
- Fixed broken handling of malformed HTTP requests made to the callback endport of :const:`~twitchAPI.eventsub.webhook.EventSubWebhook`
- Made :const:`~twitchAPI.eventsub.webhook.EventSubWebhook` more easily mockable via ``twitch-cli`` by adding :paramref:`~twitchAPI.eventsub.webhook.EventSubWebhook.subscription_url`
- Added optional subscription revokation handler via :paramref:`~twitchAPI.eventsub.webhook.EventSubWebhook.revocation_handler` to :const:`~twitchAPI.eventsub.webhook.EventSubWebhook`

PubSub
------

- Handle Authorization Revoked messages (Thanks https://github.com/Braastos )
- Added option to specify a asyncio loop via :paramref:`~twitchAPI.pubsub.PubSub.callback_loop` in which to run all callbacks in

Chat
----

- Added Chat Command Middleware, a way to decide if a command should run, see :doc:`/tutorial/chat-use-middleware` for more info.
- Added the following default Chat Command Middleware:

  - :const:`~twitchAPI.chat.middleware.ChannelRestriction`
  - :const:`~twitchAPI.chat.middleware.UserRestriction`
  - :const:`~twitchAPI.chat.middleware.StreamerOnly`
  - :const:`~twitchAPI.chat.middleware.ChannelCommandCooldown`
  - :const:`~twitchAPI.chat.middleware.ChannelUserCommandCooldown`
  - :const:`~twitchAPI.chat.middleware.GlobalCommandCooldown`

- Added option to specify a asyncio loop via :paramref:`~twitchAPI.chat.Chat.callback_loop` in which to run all callbacks in
- Fixed errors raised in callbacks not being properly reported
- Added Hype Chat related fields to :const:`~twitchAPI.chat.ChatMessage`
- Improved logging
- Fixed KeyError when encountering some Notice events
- Added new reply tags :paramref:`~twitchAPI.chat.ChatMessage.reply_thread_parent_msg_id` and :paramref:`~twitchAPI.chat.ChatMessage.reply_thread_parent_user_login` to :const:`~twitchAPI.chat.ChatMessage`
- Reconnects no longer duplicate the channel join list


OAuth
-----

- Added :const:`~twitchAPI.oauth.UserAuthenticationStorageHelper`, a easy plug and play way to generate user auth tokens only on demand

Other
-----

- Added :const:`~twitchAPI.object.base.AsyncIterTwitchObject.current_cursor()` to :const:`~twitchAPI.object.base.AsyncIterTwitchObject`
- Renamed module ``twitchAPI.types`` to :const:`twitchAPI.type`
- Moved all API related TwitchObjects from module :const:`twitchAPI.object` to :const:`twitchAPI.object.api`
- Removed default imports from module :const:`twitchAPI`


****************
Version 3.11.0
****************

Twitch
------

- Added missing field `emote_mode` to response of :const:`~twitchAPI.twitch.Twitch.get_chat_settings()` and :const:`~twitchAPI.twitch.Twitch.update_chat_settings()` (https://github.com/Teekeks/pyTwitchAPI/issues/234)

Chat
----

- Fixed timing based `AttributeError: 'NoneType' object has no attribute 'get'` in NoticeEvent during reconnect
- Ensured that only Chat Messages will ever be parsed as chat commands
- Added functionality to set per channel based prefixes (https://github.com/Teekeks/pyTwitchAPI/issues/229):

  - :const:`~twitchAPI.chat.Chat.set_channel_prefix()` to set a custom prefix for the given channel(s)
  - :const:`~twitchAPI.chat.Chat.reset_channel_prefix()` to remove a custom set prefix for the given channel(s)


****************
Version 3.10.0
****************

Twitch
------

- Added new :const:`~twitchAPI.object.ChatBadgeVersion` related fields to the following Endpoints: (Thanks https://github.com/stolenvw )

  - :const:`~twitchAPI.twitch.Twitch.get_chat_badges()`
  - :const:`~twitchAPI.twitch.Twitch.get_global_chat_badges()`

- :const:`~twitchAPI.twitch.Twitch.set_user_authentication()` now tries to refresh the given token set if it seems to be out of date
- removed the following deprecated endpoints:

  - "Replace Stream Tags"
  - "Get Stream Tags"
  - "Get All Stream Tags"
  - "Redeem Code"
  - "Get Code Status"

- Fixed condition logic when parameter `first` was given for the following Endpoints:

  - :const:`~twitchAPI.twitch.Twitch.get_chatters()` (Thanks https://github.com/d7415 )
  - :const:`~twitchAPI.twitch.Twitch.get_soundtrack_playlist()`
  - :const:`~twitchAPI.twitch.Twitch.get_soundtrack_playlists()`

PubSub
------

- PubSub now cleanly reestablishes the connection when the websocket was unexpectedly closed

****************
Version 3.9.0
****************

Twitch
------

- Added the following new Endpoints:

  - "Get Channel Followers" :const:`~twitchAPI.twitch.Twitch.get_channel_followers()`
  - "Get Followed Channels" :const:`~twitchAPI.twitch.Twitch.get_followed_channels()`

- Fixed TypeError: __api_get_request() got an unexpected keyword argument 'body' (Thanks https://github.com/JC-Chung )

EventSub
--------

- Added new Topic :const:`~twitchAPI.eventsub.EventSub.listen_channel_follow_v2()`

Chat
----

- Bot is now correctly reconnecting and rejoining channels after losing connection
- added :const:`~twitchAPI.chat.Chat.is_subscriber()` (Thanks https://github.com/stolenvw )
- added new Event :const:`~twitchAPI.types.ChatEvent.NOTICE` - Triggered when server sends a notice message (Thanks https://github.com/stolenvw )


****************
Version 3.8.0
****************

Twitch
------

- Added the new Endpoint "Send a Shoutout" :const:`~twitchAPI.twitch.Twitch.send_a_shoutout()`
- :const:`~twitchAPI.twitch.Twitch.get_users_follows()` is now marked as deprecated
- Added missing parameter :code:`type` to :const:`~twitchAPI.twitch.Twitch.get_streams()`

Helper
------

- Added new Async Generator helper :const:`~twitchAPI.helper.limit()`, with this you can limit the amount of results returned from the given AsyncGenerator to a maximum number

EventSub
--------

- Added the following new Topics:

  - "Channel Shoutout Create" :const:`~twitchAPI.eventsub.EventSub.listen_channel_shoutout_create()`
  - "Channel Shoutout Receive" :const:`~twitchAPI.eventsub.EventSub.listen_channel_shoutout_receive()`

PubSub
------

- Added new Topic "Low trust Users" :const:`~twitchAPI.pubsub.PubSub.listen_low_trust_users()`

Chat
----

- Improved rate limit handling of :const:`~twitchAPI.chat.Chat.join_room()` when joining multiple rooms per call
- The following functions now all ignore the capitalization of the given  chat room:

  - :const:`~twitchAPI.chat.Chat.join_room()`
  - :const:`~twitchAPI.chat.Chat.leave_room()`
  - :const:`~twitchAPI.chat.Chat.is_mod()`
  - :const:`~twitchAPI.chat.Chat.send_message()`

- Added :const:`initial_channel` to :const:`~twitchAPI.chat.Chat.__init__()`, with this you can auto join channels on bot startup
- Added :const:`~twitchAPI.chat.Chat.is_in_room()`
- Added :const:`~twitchAPI.chat.Chat.log_no_registered_command_handler`, with this you can control if the "no registered handler for event" warnings should be logged or not


OAuth
-----

- Added the following new AuthScopes:

  - :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_SHOUTOUTS`
  - :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_SHOUTOUTS`
  - :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_FOLLOWERS`

- Improved async handling of :const:`~twitchAPI.oauth.UserAuthenticator`


****************
Version 3.7.0
****************

Twitch
------

- Added the following Endpoints:

  - "Get AutoMod Settings" :const:`~twitchAPI.twitch.Twitch.get_automod_settings()`
  - "Update AutoMod Settings" :const:`~twitchAPI.twitch.Twitch.update_automod_settings()`

- Added :const:`~twitchAPI.twitch.Twitch.session_timeout` config. With this you can optionally change the timeout behavior across the entire library

OAuth
-----

- Added the following new AuthScopes:

  - :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_AUTOMOD_SETTINGS`
  - :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_AUTOMOD_SETTINGS`

****************
Version 3.6.2
****************

- Added :code:`py.typed` file to comply with PEP-561

Twitch
------

- Fixed all Endpoints that use :const:`~twitchAPI.object.AsyncIterTwitchObject` yielding some items multiple times
- added missing field :const:`~twitchAPI.object.TwitchUserFollow.to_login` to :const:`~twitchAPI.twitch.Twitch.get_users_follows()`

****************
Version 3.6.1
****************

EventSub
--------

- :const:`~twitchAPI.eventsub.EventSub.start()` now waits till the internal web server has fully started up

Chat
----

- Added :const:`~twitchAPI.chat.Chat.is_mod()` function (Thanks https://github.com/stolenvw )
- Made the check if the bot is a moderator in the current channel for message sending rate limiting more consistent (Thanks https://github.com/stolenvw )


****************
Version 3.5.2
****************

Twitch
------

- Fixed :const:`~twitchAPI.twitch.Twitch.end_prediction()` calling NoneType

****************
Version 3.5.1
****************

Chat
----

- Fixed KeyError in clear chat event

****************
Version 3.5.0
****************

Twitch
------

- Added the following new Endpoints:

  - "Get Charity Campaign" :const:`~twitchAPI.twitch.Twitch.get_charity_campaign()`
  - "Get Charity Donations" :const:`~twitchAPI.twitch.Twitch.get_charity_donations()`

- Fixed bug that made the user refresh token invalid in some rare edge cases

EventSub
--------

- Added the following new Topics:

  - "Charity Campaign Start" :const:`~twitchAPI.eventsub.EventSub.listen_channel_charity_campaign_start()`
  - "Charity Campaign Stop" :const:`~twitchAPI.eventsub.EventSub.listen_channel_charity_campaign_stop()`
  - "Charity Campaign Progress" :const:`~twitchAPI.eventsub.EventSub.listen_channel_charity_campaign_progress()`
  - "Charity Campaign Donate" :const:`~twitchAPI.eventsub.EventSub.listen_channel_charity_campaign_donate()`

PubSub
------

- Added :const:`~twitchAPI.pubsub.PubSub.is_connected()`
- Fixed bug that prevented a clean shutdown on Linux

Chat
----

- Added automatic rate limit handling to channel joining and message sending
- :const:`~twitchAPI.chat.Chat.send_message()` now waits till reconnected when Chat got disconnected
- :const:`~twitchAPI.chat.Chat.send_raw_irc_message()` now waits till reconnected when Chat got disconnected
- Added :const:`~twitchAPI.chat.Chat.is_connected()`
- Added :const:`~twitchAPI.chat.Chat.is_ready()`
- Chat now cleanly handles reconnect requests

OAuth
-----

- Added new Auth Scope :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_CHARITY`
- Fixed bug that prevented a clean shutdown on Linux

****************
Version 3.4.1
****************

- fixed bug that prevented newer pip versions from gathering the dependencies

****************
Version 3.4.0
****************

Twitch
------

- Added the following new Endpoints:

  - "Update Shield Mode Status" :const:`~twitchAPI.twitch.Twitch.update_shield_mode_status()`
  - "Get Shield Mode Status" :const:`~twitchAPI.twitch.Twitch.get_shield_mode_status()`

- Added the new :code:`tags` Field to the following Endpoints:

  - "Get Streams" :const:`~twitchAPI.twitch.Twitch.get_streams()`
  - "Get Followed Streams" :const:`~twitchAPI.twitch.Twitch.get_followed_streams()`
  - "Search Channels" :const:`~twitchAPI.twitch.Twitch.search_channels()`
  - "Get Channel Information" :const:`~twitchAPI.twitch.Twitch.get_channel_information()`
  - "Modify Channel Information" :const:`~twitchAPI.twitch.Twitch.modify_channel_information()`

- Improved documentation

EventSub
--------

- Added the following new Topics:

  - "Shield Mode End" :const:`~twitchAPI.eventsub.EventSub.listen_channel_shield_mode_end()`
  - "Shield Mode Begin" :const:`~twitchAPI.eventsub.EventSub.listen_channel_shield_mode_begin()`

- Improved type hints of :code:`listen_` functions
- Added check if given callback is a coroutine to :code:`listen_` functions

PubSub
------

- Fixed AttributeError when reconnecting

Chat
----

- Expanded documentation on Events and Commands
- Fixed room cache being randomly destroyed over time
- Improved message handling performance drastically for high volume chat bots
- Fixed AttributeError when reconnecting
- :const:`~twitchAPI.chat.Chat.join_room()` now times out when it was unable to join a room instead of being infinitly stuck
- :const:`~twitchAPI.chat.Chat.join_room()` now returns a list of channels it was unable to join
- Added :const:`~twitchAPI.chat.Chat.join_timeout`
- Added :const:`~twitchAPI.chat.Chat.unregister_command()`
- Added :const:`~twitchAPI.chat.Chat.unregister_event()`
- Added the following new Events:

  - :const:`~twitchAPI.types.ChatEvent.USER_LEFT` - Triggered when a user leaves a chat channel
  - :const:`~twitchAPI.types.ChatEvent.CHAT_CLEARED` - Triggered when a user was timed out, banned or the messages where deleted
  - :const:`~twitchAPI.types.ChatEvent.WHISPER` - Triggered when a user sends a whisper message to the bot

OAuth
-----

- fixed :const:`~twitchAPI.oauth.UserAuthenticator.authenticate()` getting stuck when :code:`user_token` is provided (thanks https://github.com/Tempystral )


****************
Version 3.3.0
****************

- Added new event to Chat: :const:`~twitchAPI.types.ChatEvent.MESSAGE_DELETE` which triggers whenever a single message got deleted in a channel
- Added :const:`~twitchAPI.chat.Chat.send_raw_irc_message()` method for sending raw irc commands to the websocket. Use with care!
- Fixed missing state cleanup after closing Chat, preventing the same instance from being started again
- fixed :const:`~twitchAPI.types.ChatRoom.room_id` always being Null

****************
Version 3.2.2
****************

- Fixed return type of :const:`~twitchAPI.twitch.Twitch.get_broadcaster_subscriptions()`
- removed any field starting with underscore from :const:`~twitchAPI.object.TwitchObject.to_dict()`

****************
Version 3.2.1
****************

- Fixed bug that resulted in a timeout when reading big API requests
- Optimized the use of Sessions, slight to decent performance optimization for API requests, especially for async generators

****************
Version 3.2.0
****************

- Made the used loggers available for easy logging configuration
- added the option to set the chat command prefix via :const:`~twitchAPI.chat.Chat.set_prefix()`
- :const:`~twitchAPI.twitch.Twitch.set_user_authentication()` now also throws a :const:`~twitchAPI.types.MissingScopeException` when no scope is given. (thanks https://github.com/aw-was-here )


****************
Version 3.1.1
****************

- Added the Endpoint "Get Chatters" :const:`~twitchAPI.twitch.Twitch.get_chatters()`
- Added the :const:`~twitchAPI.types.AuthScope.MODERATOR_READ_CHATTERS` AuthScope
- Added missing :const:`total` field to :const:`~twitchAPI.twitch.Twitch.get_users_follows()`
- added :const:`~twitchAPI.chat.ChatCommand.send()` shorthand to ChatCommand, this makes sending command replies easier.
- Fixed issue which prevented the Twitch client being used inside a EventSub, PubSub or Chat callback
- Fixed issue with using the wrong API url in :const:`~twitchAPI.twitch.Twitch.create_custom_reward()`
- :const:`twitchAPI.helper.first()` now returns None when there is no data to return instead of raising StopAsyncIteration exception
- Exceptions in Chat callback methods are now properly displayed

****************
Version 3.0.1
****************

- Fixed bug which resulted in :code:`Timeout context manager should be used inside a task` when subscribing to more than one EventSub topic

****************
Version 3.0.0
****************

.. note:: This Version is a major rework of the library. Please see the :doc:`v3-migration` to learn how to migrate.

**Highlights**

- Library is now fully async
- Twitch API responses are now Objects and Generators instead of pure dictionaries
- Automatic Pagination of API results
- First alpha of a Chat Bot implementation
- More customizability for the UserAuthenticator
- A lot of new Endpoints where added
- New look and content for the documentation

**Full Changelog**

* Rewrote the twitchAPI to be async
* twitchAPI now uses Objects instead of dictionaries
* added automatic pagination to all relevant API endpoints
* PubSub now uses async callbacks
* EventSub subscribing and unsubscribing is now async
* Added a alpha version of a Twitch Chat Bot implementation
* switched AuthScope `CHANNEL_MANAGE_CHAT_SETTINGS` to `MODERATOR_MANAGE_CHAT_SETTINGS`
* Added the following AuthScopes:

  * :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS`
  * :const:`~twitchAPI.types.AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES`
  * :const:`~twitchAPI.types.AuthScope.USER_MANAGE_CHAT_COLOR`
  * :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_MODERATORS`
  * :const:`~twitchAPI.types.AuthScope.CHANNEL_READ_VIPS`
  * :const:`~twitchAPI.types.AuthScope.CHANNEL_MANAGE_VIPS`
  * :const:`~twitchAPI.types.AuthScope.USER_MANAGE_WHISPERS`
* added :const:`~twitchAPI.helper.first()` helper function

* Added the following new Endpoints:

  * "Send Whisper" :const:`~twitchAPI.twitch.Twitch.send_whisper()`
  * "Remove Channel VIP" :const:`~twitchAPI.twitch.Twitch.remove_channel_vip()`
  * "Add Channel VIP" :const:`~twitchAPI.twitch.Twitch.add_channel_vip()`
  * "Get VIPs" :const:`~twitchAPI.twitch.Twitch.get_vips()`
  * "Add Channel Moderator" :const:`~twitchAPI.twitch.Twitch.add_channel_moderator()`
  * "Remove Channel Moderator" :const:`~twitchAPI.twitch.Twitch.remove_channel_moderator()`
  * "Get User Chat Color" :const:`~twitchAPI.twitch.Twitch.get_user_chat_color()`
  * "Update User Chat Color" :const:`~twitchAPI.twitch.Twitch.update_user_chat_color()`
  * "Delete Chat Message" :const:`~twitchAPI.twitch.Twitch.delete_chat_message()`
  * "Send Chat Announcement" :const:`~twitchAPI.twitch.Twitch.send_chat_announcement()`
  * "Get Soundtrack Current Track" :const:`~twitchAPI.twitch.Twitch.get_soundtrack_current_track()`
  * "Get Soundtrack Playlist" :const:`~twitchAPI.twitch.Twitch.get_soundtrack_playlist()`
  * "Get Soundtrack Playlists" :const:`~twitchAPI.twitch.Twitch.get_soundtrack_playlists()`
* Removed the folllowing deprecated Endpoints:

  * "Get Banned Event"
  * "Get Moderator Events"
  * "Get Webhook Subscriptions"
* The following Endpoints got changed:

  * Added `igdb_id` search parameter to :const:`~twitchAPI.twitch.Twitch.get_games()`
  * Removed the Voting related fields in :const:`~twitchAPI.twitch.Twitch.create_poll()` due to being deprecated
  * Updated the logic in :const:`~twitchAPI.twitch.Twitch.update_custom_reward()` to avoid API errors
  * Removed `id` parameter from :const:`~twitchAPI.twitch.Twitch.get_hype_train_events()`
  * Fixed the range check in :const:`~twitchAPI.twitch.Twitch.get_channel_information()`
* :const:`~twitchAPI.twitch.Twitch.app_auth_refresh_callback` and :const:`~twitchAPI.twitch.Twitch.user_auth_refresh_callback` are now async
* Added :const:`~twitchAPI.oauth.get_user_info()`
* UserAuthenticator:

  * You can now set the document that will be shown at the end of the Auth flow by setting :const:`~twitchAPI.oauth.UserAuthenticator.document`
  * The optional callback is now called with the access and refresh token instead of the user token
  * Added browser controls to :const:`~twitchAPI.oauth.UserAuthenticator.authenticate()`
* removed :code:`requests` and :code:`websockets` libraries from the requirements (resulting in smaller library footprint)


****************
Version 2.5.7
****************

- Fixed the End Poll Endpoint
- Properly define terminated poll status (thanks @iProdigy!)

****************
Version 2.5.6
****************

- Updated Create Prediction to take between 2 and 10 outcomes (thanks @lynara!)
- Added "Get Creator Goals" Endpoint (thanks @gitagogaming!)
- TwitchAPIException will now also include the message from the Twitch API when available

****************
Version 2.5.5
****************

- Added datetime parsing to `created_at` field for Ban User and Get Banned Users endpoints
- fixed title length check failing if the title is None for Modify Channel Information endpoint (thanks @Meduris!)

****************
Version 2.5.4
****************

- Added the following new endpoints:

  - "Ban User"

  - "Unban User"

  - "Get Blocked Terms"

  - "Add Blocked Term"

  - "Remove Blocked Term"

- Added the following Auth Scopes:

  - `moderator:manage:banned_users`

  - `moderator:read:blocked_terms`

  - `moderator:manage:blocked_terms`

- Added additional debug logging to PubSub
- Fixed KeyError when being rate limited

****************
Version 2.5.3
****************

- `Twitch.get_channel_info` now also optionally accepts a list of strings with up to 100 entries for the `broadcaster_id` parameter

****************
Version 2.5.2
****************

- Added the following new endpoints:

  - "Get Chat Settings"

  - "Update Chat Settings"

- Added Auth Scope "channel:manage:chat_settings"
- Fixed error in Auth Scope "channel:manage:schedule"
- Fixed error in Endpoint "Get Extension Transactions"
- Removed unusable Webhook code

****************
Version 2.5.1
****************

- Fixed bug that prevented EventSub subscriptions to work if main threads asyncio loop was already running

****************
Version 2.5.0
****************

- EventSub and PubSub callbacks are now executed non blocking, this fixes that long running callbacks stop the library to respond to heartbeats etc.
- EventSub subscription can now throw a TwitchBackendException when the API returns a Error 500
- added the following EventSub topics (thanks d7415!)

  - "Goal Begin"

  - "Goal Progress"

  - "Goal End"

****************
Version 2.4.2
****************

- Fixed EventSub not keeping local state in sync on unsubscribe
- Added proper exception if authentication via oauth fails

****************
Version 2.4.1
****************

- EventSub now uses a random 20 letter secret by default
- EventSub now verifies the send signature

****************
Version 2.4.0
****************

- **Implemented EventSub**

- Marked Webhook as deprecated

- added the following new endpoints

  - "Get Followed Streams"

  - "Get Polls"

  - "End Poll"

  - "Get Predictions"

  - "Create Prediction"

  - "End Prediction"

  - "Manage held AutoMod Messages"

  - "Get Channel Badges"

  - "Get Global Chat Badges"

  - "Get Channel Emotes"

  - "Get Global Emotes"

  - "Get Emote Sets"

  - "Delete EventSub Subscription"

  - "Get Channel Stream Schedule"

  - "Get Channel iCalendar"

  - "Update Channel Stream Schedule"

  - "Create Channel Stream Schedule Segment"

  - "Update Channel Stream Schedule Segment"

  - "Delete Channel Stream Schedule Segment"

  - "Update Drops Entitlements"

- Added the following new AuthScopes

  - USER_READ_FOLLOWS

  - CHANNEL_READ_POLLS

  - CHANNEL_MANAGE_POLLS

  - CHANNEL_READ_PREDICTIONS

  - CHANNEL_MANAGE_PREDICTIONS

  - MODERATOR_MANAGE_AUTOMOD

  - CHANNEL_MANAGE_SCHEDULE

- removed deprecated Endpoints

  - "Create User Follows"

  - "Delete User Follows"

- Added Topics to PubSub

  - "AutoMod Queue"

  - "User Moderation Notifications"

- Check if at least one of status or id is provided in get_custom_reward_redemption
- reverted change that made reward_id optional in get_custom_reward_redemption
- get_extension_transactions now takes up to 100 transaction ids
- added delay parameter to modify_channel_information
- made parameter prompt of create_custom_reward optional and changed parameter order
- made reward_id of get_custom_reward take either a list of str or str
- made parameter title, prompt and cost optional in update_custom_reward
- made parameter redemption_ids of update_redemption_status take either a list of str or str
- fixed exception in block_user
- allowed Twitch.check_automod_status to take in more that one entry

****************
Version 2.3.2
****************

* fixed get_custom_reward_redemption url (thanks iProdigy!)
* made reward_id parameter of get_custom_reward_redemption optional

****************
Version 2.3.1
****************

* fixed id parameter for get_clips of Twitch

****************
Version 2.3.0
****************

* Initializing the Twitch API now automatically creates a app authorization (can be disabled via flag)
* Made it possible to not set a app secret in cases where only user authentication is required
* added helper function `validate_token` to OAuth
* added helper function `revoke_token` to OAuth
* User OAuth Token is now automatically validated for correct scope and validity when being set
* added new "Get Drops Entitlement" endpoint
* added new "Get Teams" endpoint
* added new "Get Chattel teams" endpoint
* added new AuthScope USER_READ_SUBSCRIPTIONS
* fixed exception in Webhook if no Authentication is set and also not required
* refactored Authentication handling, making it more versatile
* added more debugging logs
* improved documentation

****************
Version 2.2.5
****************

* added optional callback to Twitch for user and app access token refresh
* added additional check for non empty title in Twitch.modify_channel_information
* changed required scope of PubSub.listen_channel_subscriptions from CHANNEL_SUBSCRIPTIONS to CHANNEL_READ_SUBSCRIPTIONS


****************
Version 2.2.4
****************

* added Python 3.9 compatibility
* improved example for PubSub

****************
Version 2.2.3
****************

* added new "get channel editors" endpoint
* added new "delete videos" endpoint
* added new "get user block list" endpoint
* added new "block user" endpoint
* added new "unblock user" endpoint
* added new authentication scopes
* some refactoring

****************
Version 2.2.2
****************

* added missing API base url to delete_custom_reward, get_custom_reward, get_custom_reward_redemption and update_redemption_status (thanks asphaltschneider!)

****************
Version 2.2.1
****************

* added option to set a ssl context to be used by Webhook
* fixed modify_channel_information throwing ValueError (thanks asishm!)
* added default route to Webhook on / for easier debugging
* properly check for empty lists in the selection of the used AuthScope in get_users
* raise ValueError if both from_id and to_id are None in subscribe_user_follow of Webhook

****************
Version 2.2.0
****************

* added missing "Create custom rewards" endpoint
* added missing "Delete Custom rewards" endpoint
* added missing "Get Custom Reward" endpoint
* added missing "Get custom reward redemption" endpoint
* added missing "Update custom Reward" endpoint
* added missing "Update redemption status" endpoint
* added missing pagination parameters to endpoints that support them
* improved documentation
* properly handle 401 response after retries

****************
Version 2.1
****************

Added a Twitch PubSub client implementation.

See :doc:`modules/twitchAPI.pubsub` for more Info!

* added PubSub client
* made UserAuthenticator URL dynamic
* added named loggers for all modules
* fixed bug in Webhook.subscribe_subscription_events
* added Twitch.get_user_auth_scope

****************
Version 2.0.1
****************

Fixed some bugs and implemented changes made to the Twitch API

****************
Version 2.0
****************

This version is a major overhaul of the Webhook, implementing missing and changed API endpoints and adding a bunch of quality of life changes.

* Reworked the entire Documentation
* Webhook subscribe and unsubscribe now waits for handshake to finish
* Webhook now refreshes its subscriptions
* Webhook unsubscribe is now a single function
* Webhook auto unsubscribes from topics on stop()
* Added unsubscribe_all function to Webhook
* Twitch instance now auto renews auth token once they become invalid
* Added retry on API backend error
* Added get_drops_entitlements endpoint
* Fixed function signature of get_webhook_subscriptions
* Fixed update_user_extension not writing data
* get_user_active_extensions now requires User Authentication
* get_user_follows now requires at elast App Authentication
* get_users now follows the changed API Authentication logic
* get_stream_markers now also checks that at least one of user_id or video_id is provided
* get_streams now takes a list for game_id
* get_streams now checks the length of the language list
* get_moderator_events now takes in a list of user_ids
* get_moderators now takes in a list of user_ids
* get_clips can now use the first parameter
* Raise exception when twitch backend returns 503 even after a retry
* Now use custom exception classes
* Removed depraced endpoint get_streams_metadata
