:orphan:

v2 to v3 migration guide
========================

With version 3, this library made the switch from being mixed sync and async to being fully async.
On top of that, it also switched from returning the mostly raw api response as dictionaries over to using objects and generators, making the overall usability easier.

But this means that v2 and v3 are not compatible.

In this guide I will give some basic help on how to migrate your existing code.

.. note:: This guide will only show a few examples, please read the documentation for everything you use carefully, its likely that something has changed with every single one!


**Please note that any call mentioned here that starts with a :code:`await` will have to be called inside a async function even if not displayed as such!**


Library Initialization
----------------------

You now need to await the Twitch Object and refresh callbacks are now async.

.. code-block:: python
    :caption: V2 (before)

    from twitchAPI.twitch import Twitch

    def user_refresh(token: str, refresh_token: str):
        print(f'my new user token is: {token}')

    def app_refresh(token: str):
        print(f'my new app token is: {token}')

    twitch = Twitch('app_id', 'app_secret')
    twitch.app_auth_refresh_callback = app_refresh
    twitch.user_auth_refresh_callback = user_refresh


.. code-block:: python
    :caption: V3 (now)

    from twitchAPI.twitch import Twitch

    async def user_refresh(token: str, refresh_token: str):
        print(f'my new user token is: {token}')

    async def app_refresh(token: str):
        print(f'my new app token is: {token}')

    twitch = await Twitch('my_app_id', 'my_app_secret')
    twitch.app_auth_refresh_callback = app_refresh
    twitch.user_auth_refresh_callback = user_refresh


Working with the API results
----------------------------

As detailed above, the API now returns Objects instead of pure dictionaries.

Below are how each one has to be handled. View the documentation of each API method to see which type is returned.

TwitchObject
^^^^^^^^^^^^

A lot of API calls return a child of :py:const:`~twitchAPI.object.TwitchObject` in some way (either directly or via generator).
You can always use the :py:const:`~twitchAPI.object.TwitchObject.to_dict()` method to turn that object to a dictionary.

Example:

.. code-block:: python

    blocked_term = await twitch.add_blocked_term('broadcaster_id', 'moderator_id', 'bad_word')
    print(blocked_term.id)


IterTwitchObject
^^^^^^^^^^^^^^^^

Some API calls return a special type of TwitchObject.
These usually have some list inside that you may want to dicrectly itterate over in your API usage but that also contain other usefull data
outside of that List.


Example:

.. code-block:: python

    lb = await twitch.get_bits_leaderboard()
    print(lb.total)
    for e in lb:
        print(f'#{e.rank:02d} - {e.user_name}: {e.score}')


AsyncIterTwitchObject
^^^^^^^^^^^^^^^^^^^^^

A few API calls will have usefull data outside of the list the pagination itterates over.
For those cases, this object exist.

Example:

.. code-block:: python

    schedule = await twitch.get_channel_stream_schedule('user_id')
    print(schedule.broadcaster_name)
    async for segment in schedule:
        print(segment.title)


AsyncGenerator
^^^^^^^^^^^^^^

AsyncGenerators are used to automatically itterate over all possible resuts of your API call, this will also automatically handle pagination for you.
In some cases (for example stream schedules with repeating entries), this may result in a endless stream of entries returned so make sure to add your own
exit conditions in such cases.
The generated objects will always be children of :py:const:`~twitchAPI.object.TwitchObject`, see the docs of the API call to see the exact object type.

Example:

.. code-block:: python

    async for tag in twitch.get_all_stream_tags():
        print(tag.tag_id)


PubSub
------

All callbacks are now async.

.. code-block:: python
    :caption: V2 (before)

    # this will be called
    def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)

.. code-block:: python
    :caption: V3 (now)

    async def callback_whisper(uuid: UUID, data: dict) -> None:
        print('got callback for UUID ' + str(uuid))
        pprint(data)


EventSub
--------

All `listen_` and `unsubscribe_` functions are now async

.. code-block:: python
    :caption: listen and unsubscribe in V2 (before)

    event_sub.unsubscribe_all()
    event_sub.listen_channel_follow(user_id, on_follow)

.. code-block:: python
    :caption: listen and unsubscribe in V3 (now)

    await event_sub.unsubscribe_all()
    await event_sub.listen_channel_follow(user_id, on_follow)


:const:`~twitchAPI.eventsub.EventSub.stop()` is now async

.. code-block:: python
    :caption: stop() in V2 (before)

    event_sub.stop()

.. code-block:: python
    :caption: stop() in V3 (now)

    await event_sub.stop()
