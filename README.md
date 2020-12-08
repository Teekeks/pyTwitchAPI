# Python Twitch API

[![PyPI verion](https://img.shields.io/pypi/v/twitchAPI.svg)](https://pypi.org/project/twitchAPI/) [![PyPI verion](https://img.shields.io/pypi/pyversions/twitchAPI)](https://pypi.org/project/twitchAPI/) [![Twitch API version](https://img.shields.io/badge/twitch%20API%20version-Helix-brightgreen)](https://dev.twitch.tv/docs/api) [![Documentation Status](https://readthedocs.org/projects/pytwitchapi/badge/?version=latest)](https://pytwitchapi.readthedocs.io/en/latest/?badge=latest)


This is a full implementation of the Twitch API, its Webhook and PubSub in python 3.7.  


## Installation

Install using pip:

```pip install twitchAPI```

## Documentation

A full API documentation can be found [on readthedocs.org](https://pytwitchapi.readthedocs.io/en/latest/index.html).

## Usage

### Basic API calls

Setting up a Instance of the Twitch API and get your User ID:

```python
from twitchAPI.twitch import Twitch

# create instance of twitch API
twitch = Twitch('my_app_id', 'my_app_secret')
twitch.authenticate_app([])

# get ID of user
user_info = twitch.get_users(logins=['my_username'])
user_id = user_info['data'][0]['id']
```

### Authentication

The Twitch API knows 2 different authentications. App and User Authentication.
Which one you need (or if one at all) depends on what calls you want to use.

Its always good to get at least App authentication even for calls where you dont need it since the rate limmits are way better for authenticated calls.

#### App Authentication

App authentication is super simple, just do the following:

```python
from twitchAPI.twitch import Twitch
twitch = Twitch('my_app_id', 'my_app_secret')
# add App authentication
twitch.authenticate_app([])
```
### User Authentication

To get a user auth token, the user has to explicitly click "Authorize" on the twitch website. You can use various online services to generate a token or use my build in authenticator.
For my authenticator you have to add the following URL as a "OAuth Redirect URL": ```http://localhost:17563```
You can set that [here in your twitch dev dashboard](https://dev.twitch.tv/console).


```python
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope

twitch = Twitch('my_app_id', 'my_app_secret')

target_scope = [AuthScope.BITS_READ]
auth = UserAuthenticator(twitch, target_scope, force_verify=False)
# this will open your default browser and prompt you with the twitch verification website
token, refresh_token = auth.authenticate()
# add User authentication
twitch.set_user_authentication(token, target_scope, refresh_token)
```

You can reuse this token and use the refresh_token to renew it:

```python
from twitchAPI.oauth import refresh_access_token
new_token, new_refresh_token = refresh_access_token('refresh_token', 'client_id', 'client_secret')
```



### Webhook

See [webhook_example.py](../master/webhook_example.py) for a full example usage. 

A more detailed documentation can be found [here on readthedocs](https://pytwitchapi.readthedocs.io/en/latest/modules/twitchAPI.webhook.html).

#### Requirements

You need to have a public IP with a port open. That port will be 80 by default.
Authentication is off by default but you can choose to authenticate to use some Webhook Topics or to get more information.  
**Please note that Your Endpoint URL has to be HTTPS if you choose to authenticate which means that you probably need a reverse proxy like nginx.**


### Start Webhook

Example on how to set up a webhook and start it:
````python
from twitchAPI.twitch import Twitch
from twitchAPI.webhook import TwitchWebHook

twitch = Twitch('my_app_id', 'my_app_secret')
# add App authentication
twitch.authenticate_app([])

# Note that you have to use https as soon as you use functions that require authentication (most of them)
hook = TwitchWebHook("https://my.cool.ip:8080", 'your app id', 8080)
# some hooks dont require any authentication, which would remove the requirement to set up a https reverse proxy
# if you dont require authentication just dont call authenticate()
hook.authenticate(twitch)
hook.start()
````

### Subscribing to Webhook Topics
Define a callback function and subscribe to a event:
````python
from uuid import UUID
from pprint import pprint

def callback_user_changed(uuid: UUID, data: dict) -> None:
    print(f'Callback for UUID {str(uuid)}')
    pprint(data)

success, sub_uuid = hook.subscribe_user_changed(user_id, callback_user_changed)
````
The subscription function returns a UUID that identifies this subscription. This means you can use the same callback function for multiple subscriptions.

### Unsubscribing

To unsubscribe, just use that UUID from the subscription:
```python
success = hook.unsubscribe_user_changed(sub_uuid)
```

### Stopping the Webhook

Stopping the webhook:
```python
hook.stop()
```

### Unsubscribing from any remaining active Webhook topic

Should your management of webhook subscriptions fail (due to a crash or something else) and there is a active webhook remaining after your program closed, you may use the following:

```python
hook.unsubscribe_all(twitch)
```

The parameter is a ``twitchAPI.twitch.Twitch`` instance with app authentication.


## PubSub

PubSub enables you to subscribe to a topic, for updates (e.g., when a user cheers in a channel).

A more detailed documentation can be found [here on readthedocs](https://pytwitchapi.readthedocs.io/en/latest/modules/twitchAPI.pubsub.html)

```python
from twitchAPI.pubsub import PubSub
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope
from pprint import pprint
from uuid import UUID

def callback_whisper(uuid: UUID, data: dict) -> None:
    print('got callback for UUID ' + str(uuid))
    pprint(data)

# setting up Authentication and getting your user id
twitch = Twitch('my_app_id', 'my_app_secret')
twitch.authenticate_app([])
twitch.set_user_authentication('my_user_auth_token', [AuthScope.WHISPERS_READ], 'my_user_auth_refresh_token')
user_id = twitch.get_users(logins=['my_username'])['data'][0]['id']

# starting up PubSub
pubsub = PubSub(twitch)
pubsub.start()
# you can either start listening before or after you started pubsub.
uuid = pubsub.listen_whispers(user_id, callback_whisper)
input('press ENTER to close...')
# you do not need to unlisten to topics before stopping but you can listen and unlisten at any moment you want
pubsub.unlisten(uuid)
pubsub.stop()
```
