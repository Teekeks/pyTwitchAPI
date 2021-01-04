.. twitchAPI_changelog:

Changelog
=====================================

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
