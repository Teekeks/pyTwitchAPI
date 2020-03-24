#  Copyright (c) 2020. Lena "Teekeks" During <info@teawork.de>

ANALYTICS_READ_EXTENSION = 'analytics:read:extensions'
ANALYTICS_READ_GAMES = 'analytics:read:games'
BITS_READ = 'bits:read'
CHANNEL_READ_SUBSCRIPTIONS = 'channel:read:subscriptions'
CLIPS_EDIT = 'clips:edit'
USER_EDIT = 'user:edit'
USER_EDIT_BROADCAST = 'user:edit:broadcast'
USER_READ_BROADCAST = 'user:read:broadcast'
USER_READ_EMAIL = 'user:read:email'


def build_scope(*scopes) -> str:
    return ' '.join(scopes)
