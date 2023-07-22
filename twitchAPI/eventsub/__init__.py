#  Copyright (c) 2023. Lena "Teekeks" During <info@teawork.de>
"""
EventSub
--------

.. warning:: Rework in progress, docs not accurate

EventSub lets you listen for events that happen on Twitch.

The EventSub client runs in its own thread, calling the given callback function whenever an event happens.

Look at the `Twitch EventSub reference <https://dev.twitch.tv/docs/eventsub/eventsub-reference>`__ to find the topics
you are interested in.

Available Transports
====================

EventSub is available with different types of transports, used for different applications.

.. list-table::
   :header-rows: 1

   * - Transport Method
     - Use Case
     - Auth Type
   * - :doc:`twitchAPI.eventsub.webhook`
     - Server / Multi User
     - App Authentication
   * - :doc:`twitchAPI.eventsub.websocket`
     - Client / Single User
     - User Authentication


.. toctree::
   :hidden:
   :maxdepth: 1

   twitchAPI.eventsub.webhook
   twitchAPI.eventsub.websocket

"""
