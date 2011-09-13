from django.conf.urls.defaults import *

UID = '(?P<uid>[A-Za-z0-9_]*)'
ROOM = '(?P<room_id>[A-Za-z0-9-]*)'
MESSAGE = '(?P<message>.*)'
MATCH = '(?P<matchid>[A-Za-z0-9_]*)'

urlpatterns = patterns('gauss.chat.views',
    url(r"^chatroom/%s/$" % MATCH, 'chatroom', name="chat_room"),
    url(r"^window/%s/%s/$" % (UID, ROOM), 'window', name="chat_window"),
    url(r"^message/%s/%s/%s/$" % (UID, ROOM, MESSAGE),
        'message', name="chat_message"),
)

