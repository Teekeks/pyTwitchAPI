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
