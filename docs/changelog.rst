.. twitchAPI_changelog:

Changelog
=====================================

****************
Version 2.5.2
****************

- Added the following new endpoints:

  - "Get Chat Settings"

  - "Update Chat Settings"

- Added Auth Scope "channel:manage:chat_settings"
- Fixed error in Auth Scope "channel:manage:schedule"
- Fixed error in Endpoint "Get Extension Transactions"

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
