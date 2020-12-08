.. twitchAPI documentation master file, created by
   sphinx-quickstart on Sat Mar 28 12:49:23 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Twitch API
=====================================

This is a full implementation of the Twitch Helix API, its Webhook and PubSub in python 3.7.

On Github: https://github.com/Teekeks/pyTwitchAPI

On PyPi: https://pypi.org/project/twitchAPI/

Visit the :doc:`changelog` to see what has changed.

Installation
============

Install using pip:

```pip install twitchAPI```


Usage
=====

For more detailed usage examples, see the links below

.. code-block:: python

    from twitchAPI.twitch import Twitch
    from pprint import pprint
    twitch = Twitch('my_app_key', 'my_app_secret')
    # lets create a simple app authentication:
    twitch.authenticate_app([])
    pprint(twitch.get_users(logins=['your_twitch_username']))


Logging
=======

This module uses the `logging` module for creating Logs.
Valid loggers are:

* `twitchAPI.twitch`
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
   twitchAPI.webhook
   twitchAPI.pubsub
   twitchAPI.oauth
   twitchAPI.types
   twitchAPI.helper
