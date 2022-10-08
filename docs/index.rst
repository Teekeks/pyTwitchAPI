.. twitchAPI documentation master file, created by
   sphinx-quickstart on Sat Mar 28 12:49:23 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Twitch API
=====================================

This is a full implementation of the Twitch Helix API, its Webhook, PubSub and EventSub in python 3.7+.

On Github: https://github.com/Teekeks/pyTwitchAPI

On PyPi: https://pypi.org/project/twitchAPI/

Visit the :doc:`changelog` to see what has changed.

Installation
============

Install using pip:

```pip install twitchAPI```

Support
=======

For Support please join the `Twitch API Discord server <https://discord.gg/tu2Dmc7gpd>`_.

Usage
=====

For more detailed usage examples, see the links below

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from twitchAPI.helper import first
    import asyncio

    async def twitch_example():
        # initialize the twitch instance, this will by default also create a app authentication for you
        twitch = await Twitch('app_id', 'app_secret')
        # call the API for the data of your twitch user
        # this returns a async generator that can be used to iterate over all results
        # but we are just interested in the first result
        # using the first helper makes this easy.
        user = await first(twitch.get_users(logins='your_twitch_user'))
        # print the ID of your user or do whatever else you want with it
        print(user.id)

    # run this example
    asyncio.run(twitch_example())


See `twitchAPI.twitch` for more details on how to set Authentication.

Logging
=======

This module uses the `logging` module for creating Logs.
Valid loggers are:

* `twitchAPI.twitch`
* `twitchAPI.eventsub`
* `twitchAPI.pubsub`
* `twitchAPI.oauth`
* `twitchAPI.webhook`

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :doc:`changelog`


.. autosummary::
   :toctree: modules

   twitchAPI.twitch
   twitchAPI.eventsub
   twitchAPI.pubsub
   twitchAPI.webhook
   twitchAPI.oauth
   twitchAPI.types
   twitchAPI.helper
   twitchAPI.object
