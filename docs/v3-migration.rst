v2 to v3 migration guide
========================

With version 3, this library made the switch from being mixed sync and async to being fully async.
On top of that, it also switched from returning the mostly raw api response as dictionaries over to using objects and generators, making the overall usability easier.

But this means that v2 and v3 are not compatible.

In this guide I will give some basic help on how to migrate your existing code.

.. note:: This guide will only show a few examples, please read the documentation for everything you use carefully, its likely that something has changed with every single one!


Library Initialization
----------------------

You now need to await the Twitch Object.

.. code-block:: python
    :caption: V2 (before)

    twitch = Twitch('app_id', 'app_secret')


.. code-block:: python
    :caption: V3 (now)

    twitch = await Twitch('app_id', 'app_secret')



Objects
-------

The library now returns Objects instead of dictionaries.
You can see which fields are available inside the Documentation.\n
If you would rather have the result as a dictionary you can always call `.to_dict()` on any of these objects.

Should you be only interested in the first result, you can use the :const:`~twitchAPI.helper.first()` helper method as shown below.

.. code-block:: python
    :caption: V2 (before)

    user = twitch.get_users(logins='my_twitch_name')
    user_id = user['data'][0]['id']

.. code-block:: python
    :caption: V3 (now)

    user = await first(twitch.get_users(logins='my_twitch_name'))
    user_id = user.id


Pagination
----------

Before, you where required to use the cursor yourself to itterate over all pages of the result, this is no longer required.

.. code-block:: python
    :caption: V2 (before)

    after = None
    while True:
        resp = twitch.get_all_stream_tags(after=after)
        for tag in resp['data']:
            print(tag['tag_id'])
        after = resp['pagination'].get('cursor')
        if after is None:
            break

.. code-block:: python
    :caption: V3 (now)

    async for tag in twitch.get_all_stream_tags():
        print(tag.tag_id)



Working with the API results
----------------------------

The API returns a few different types of results.


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
