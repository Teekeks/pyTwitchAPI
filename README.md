# Python Twitch API

This is a python 3.7 implementation of the Twitch API and its Webhook.  
**At the current time, only the Webhook is fully implemented!**

## Installation

Install using pip:

```pip install twitchAPI```

## Usage

### Basic API calls

Setting up a Instance of the Twitch API and get your User ID:
```python
from twitchAPI.twitch import Twitch
import twitchAPI.scope as scope

# create instance of twitch API
twitch = Twitch('my_app_id', 'my_app_secret', scope.build_scope(scope.USER_READ_EMAIL))

# get ID of user
user_info = twitch.get_users(logins=['my_username'])
user_id = user_info[0]['id']
```

### Webhook

Authentication is off by default but you can choose to authenticate to use some Webhook Topics or to get more information.
Please note that Your Endpoint URL has to be HTTPS if you choose to authenticate which means that you probably need a reverse proxy like nginx.

Example on how to set up a webhook and start it:
````python
hook = twitch.get_webhook('https://my.url.com', port=80)
hook.authenticate(twitch.get_auth_token())
hook.secret = 'some_fancy_long_secret_string'
hook.start()
````

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

To unsubscribe, just use that UUID from the subscription:
```python
success = hook.unsubscribe_user_changed(sub_uuid)
```

Stopping the webhook:
```python
hook.stop()
```
