from twitchAPI import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope
from twitchAPI.webhook import TwitchWebHook
from pprint import pprint


def callback_stream_changed(uuid, data):
    print('Callback Stream changed for UUID ' + str(uuid))
    pprint(data)


def callback_user_changed(uuid, data):
    print('Callback User changed for UUID ' + str(uuid))
    pprint(data)


# basic twitch API authentication, this will yield a app token but not a user token
twitch = Twitch('your app id', 'your app secret')
twitch.authenticate_app([])
# since we want user information, we require a OAuth token, lets get one
# you dont need to generate a fresh user token every time, you can also refresh a old one or get one using a different online service
# for refreshing look here: https://github.com/Teekeks/pyTwitchAPI#user-authentication
# please note that you have to add http://localhost:17563 as a OAuth redirect URL for your app, see the above link for more information
auth = UserAuthenticator(twitch, [AuthScope.USER_READ_EMAIL])
token, refresh_token = auth.authenticate()  # this will open a webpage
twitch.set_user_authentication(token, [AuthScope.USER_READ_EMAIL], refresh_token)  # setting the user authentication so any api call will also use it
# setting up the Webhook itself
hook = TwitchWebHook("https://my.cool.ip:8080", 'your app id', 8080)
hook.authenticate(twitch)  # this will use the highest authentication set, which is the user authentication.
# some hooks don't require any authentication, which would remove the requirement to set up a https reverse proxy
# if you don't require authentication just dont call authenticate()
hook.start()

# the hook has to run before you subscribe to any events since the twitch api will do a handshake this this webhook as soon as you subscribe
success, uuid_stream = hook.subscribe_stream_changed('your user id', callback_stream_changed)
print(f'was subscription successfull?: {success}')
success, uuid_user = hook.subscribe_user_changed('your user id', callback_user_changed)
print(f'was subscription successfull?: {success}')

# now we are fully set up and listening to our webhooks, lets wait for a user imput to stop again:
input('Press enter to stop...')

# lets unsubscribe again
success = hook.unsubscribe(uuid_user)
print(f'was unsubscription successfull?: {success}')
# since hook.unsubscribe_on_stop is true, we dont need to unsubscribe manually, so lets just stop
hook.stop()
