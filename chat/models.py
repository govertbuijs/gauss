from datetime import datetime, timedelta
import uuid

from django.db import models

from gauss.restapi.models import User, Match


CHAT_TIME_OUT = 15 * 60
CHAT_SUSPEND = 2 * 60


class Room(models.Model):
    room_id = models.CharField(max_length=36)
    match = models.ForeignKey(Match)
    created = models.DateTimeField(editable=False, auto_now_add=True)

    def get_messages(self, uid):
        if self.created + timedelta(seconds=CHAT_TIME_OUT) < datetime.now():
            return False, ["This connection has timed out"]

        messages = []
        for message in ChatMessage.objects.filter(room=self):
            if uid == message.user.device_id:
                messages.append("You : %s" % message.text)
            else:
                messages.append("Stranger : %s" % message.text)

        if self.created + timedelta(seconds=CHAT_SUSPEND) < datetime.now():
            messages.append("This connection is suspended")

        return True, messages

    def create_room(self):
        self.room_id = unicode(uuid.uuid4())
        self.save()


class ChatMessage(models.Model):
    user = models.ForeignKey(User, related_name='chat_messages')
    room = models.ForeignKey(Room)
    text = models.TextField(null=True, blank=True)
    created = models.DateTimeField(editable=False, auto_now_add=True)

