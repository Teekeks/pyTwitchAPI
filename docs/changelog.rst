.. twitchAPI_changelog:

Changelog
=====================================

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
