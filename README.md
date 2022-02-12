# Python Twitch API

[![PyPI verion](https://img.shields.io/pypi/v/twitchAPI.svg)](https://pypi.org/project/twitchAPI/) [![Python version](https://img.shields.io/pypi/pyversions/twitchAPI)](https://pypi.org/project/twitchAPI/) [![Twitch API version](https://img.shields.io/badge/twitch%20API%20version-Helix-brightgreen)](https://dev.twitch.tv/docs/api) [![Documentation Status](https://readthedocs.org/projects/pytwitchapi/badge/?version=latest)](https://pytwitchapi.readthedocs.io/en/latest/?badge=latest)


This is a full implementation of the Twitch API, its Webhook and PubSub in python 3.7.  


## Installation

Install using pip:

```pip install twitchAPI```

## Documentation and Support

A full API documentation can be found [on readthedocs.org](https://pytwitchapi.readthedocs.io/en/latest/index.html).

For support please join the [Twitch API discord server](https://discord.gg/tu2Dmc7gpd)

## Usage

### Basic API calls

Setting up a Instance of the Twitch API and get your User ID:

```python
from twitchAPI.twitch import Twitch

# create instance of twitch API and create app authentication
twitch = Twitch('my_app_id', 'my_app_secret')

# get ID of user
user_info = twitch.get_users(logins=['my_username'])
user_id = user_info['data'][0]['id']
```

### Authentication

The Twitch API knows 2 different authentications. App and User Authentication.
Which one you need (or if one at all) depends on what calls you want to use.

It's always good to get at least App authentication even for calls where you don't need it since the rate limits are way better for authenticated calls.

**Please read the docs for more details and examples on how to set and use Authentication!**

#### App Authentication

App authentication is super simple, just do the following:

```python
from twitchAPI.twitch import Twitch
twitch = Twitch('my_app_id', 'my_app_secret')
```

### User Authentication

To get a user auth token, the user has to explicitly click "Authorize" on the twitch website. You can use various online services to generate a token or use my build in Authenticator.
For my Authenticator you have to add the following URL as a "OAuth Redirect URL": ```http://localhost:17563```
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

### AuthToken refresh callback

Optionally you can set a callback for both user access token refresh and app access token refresh.

```python
from twitchAPI.twitch import Twitch

def user_refresh(token: str, refresh_token: str):
    print(f'my new user token is: {token}')

def app_refresh(token: str):
    print(f'my new app token is: {token}')

twitch = Twitch('my_app_id', 'my_app_secret')
twitch.app_auth_refresh_callback = app_refresh
twitch.user_auth_refresh_callback = user_refresh
```


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


## EventSub

### Requirements


You need to have a public IP with a port open. That port will be 80 by default.
You need app authentication and your Endpoint URL must point to a

**Please note that Your Endpoint URL has to be HTTPS, has to run on Port 443 and requires a valid, non self signed certificate
This most likely means, that you need a reverse proxy like nginx. You can also hand in a valid ssl context to be used in the constructor.**

You can check on whether or not your webhook is publicly reachable by navigating to the URL set in `callback_url`.
You should get a 200 response with the text `pyTwitchAPI eventsub`.

### Listening to topics

After you started your EventSub client, you can use the `listen_` prefixed functions to listen to the topics you are interested in.

The function you hand in as callback will be called whenever that event happens with the event data as a parameter.

### Short code example:

```python
from pprint import pprint
from twitchAPI import Twitch, EventSub

# this will be called whenever someone follows the target channel
async def on_follow(data: dict):
    pprint(data)

TARGET_USERNAME = 'target_username_here'
WEBHOOK_URL = 'https://url.to.your.webhook.com'
APP_ID = 'your_app_id'
APP_SECRET = 'your_app_secret'

twitch = Twitch(APP_ID, APP_SECRET)
twitch.authenticate_app([])

uid = twitch.get_users(logins=[TARGET_USERNAME])
user_id = uid['data'][0]['id']
# basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
hook = EventSub(WEBHOOK_URL, APP_ID, 8080, twitch)
# unsubscribe from all to get a clean slate
hook.unsubscribe_all()
# start client
hook.start()
print('subscribing to hooks:')
hook.listen_channel_follow(user_id, on_follow)

try:
    input('press Enter to shut down...')
finally:
    hook.stop()
print('done')
```
