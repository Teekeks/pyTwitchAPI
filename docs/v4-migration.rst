:orphan:

v3 to v4 migration guide
========================

With v4 of this library, some modules got reorganized and EventSub got a bunch of major changes.

In this guide I will give some basic help on how to migrate your existing code.


General module changes
----------------------

- ``twitchAPI.types`` was renamed to :const:`twitchAPI.type`
- Most objects where moved from ``twitchAPI.object`` to :const:`twitchAPI.object.api`
- The following Objects where moved from ``twitchAPI.object`` to :const:`twitchAPI.object.base`:

  - :const:`~twitchAPI.object.base.TwitchObject`
  - :const:`~twitchAPI.object.base.IterTwitchObject`
  - :const:`~twitchAPI.object.base.AsyncIterTwitchObject`

EventSub
--------

Eventsub has gained a new transport, the old ``EventSub`` is now located in the module :const:`twitchAPI.eventsub.webhook` and was renamed to :const:`~twitchAPI.eventsub.webhook.EventSubWebhook`

Topic callbacks now no longer use plain dictionaries but objects. See :ref:`eventsub-available-topics` for more information which topic uses which object.

.. code-block:: python
   :caption: V3 (before)

    from twitchAPI.eventsub import EventSub
    import asyncio

    EVENTSUB_URL = 'https://url.to.your.webhook.com'


    async def on_follow(data: dict):
        print(data)


    async def eventsub_example():
        # twitch setup is left out of this example

        event_sub = EventSub(EVENTSUB_URL, APP_ID, 8080, twitch)
        await event_sub.unsubscribe_all()
        event_sub.start()
        await event_sub.listen_channel_follow_v2(user.id, user.id, on_follow)

        try:
            input('press Enter to shut down...')
        finally:
            await event_sub.stop()
            await twitch.close()
        print('done')


    asyncio.run(eventsub_example())


.. code-block:: python
   :caption: V4 (now)

    from twitchAPI.eventsub.webhook import EventSubWebhook
    from twitchAPI.object.eventsub import ChannelFollowEvent
    import asyncio

    EVENTSUB_URL = 'https://url.to.your.webhook.com'


    async def on_follow(data: ChannelFollowEvent):
        print(f'{data.event.user_name} now follows {data.event.broadcaster_user_name}!')


    async def eventsub_webhook_example():
        # twitch setup is left out of this example

        eventsub = EventSubWebhook(EVENTSUB_URL, 8080, twitch)
        await eventsub.unsubscribe_all()
        eventsub.start()
        await eventsub.listen_channel_follow_v2(user.id, user.id, on_follow)

        try:
            input('press Enter to shut down...')
        finally:
            await eventsub.stop()
            await twitch.close()
        print('done')


    asyncio.run(eventsub_webhook_example())
