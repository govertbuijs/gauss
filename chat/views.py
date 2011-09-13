from datetime import datetime, timedelta
import json
import time

from django.http import HttpResponse

from gauss.chat.models import Room, ChatMessage, CHAT_SUSPEND
from gauss.restapi.models import User, Match, MATCH_STATUS_CHOICES


def chatroom(request, matchid):
    # Get corresponding match
    try:
        match = Match.objects.get(id=matchid)
    except:
        response = {"Success": "False", "Error": "Match not found" }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    # Check status of match
    if int(match.status) >= 90:
        status = dict(MATCH_STATUS_CHOICES).get(match.status)
        response = {"Success": "False", "Error": status, }
        return HttpResponse(json.dumps(response), mimetype="text/plain")
    if match.last_activity + timedelta(minutes=CHAT_SUSPEND) < datetime.now():
        response = {"Success": "False", "Error": "Chat suspended", }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    # Try getting the room, else make it
    try:
        room = Room.objects.get(match=match)
    except:
        room = Room(match=match)
        room.create_room()

    response = {"Success": "True", "Roomid": room.room_id, }
    return HttpResponse(json.dumps(response), mimetype="text/plain")


def window(request, uid, room_id):
    try:
        room = Room.objects.get(room_id=room_id)
    except:
        response = {"Success": "False", "Error": "Room doesn't exist", }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    status, messages = room.get_messages(uid)

    response = {"Success": str(status), "Messages": messages, }
    return HttpResponse(json.dumps(response), mimetype="text/plain")


def message(request, uid, room_id, message):
    try:
        user = User.objects.get(device_id=uid)
    except:
        response = {"Success": "False", "Error": "User doesn't exist", }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    try:
        room = Room.objects.get(room_id=room_id)
    except:
        response = {"Success": "False", "Error": "Room doesn't exist", }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    # Check if user is allewod to
    if room.created + timedelta(minutes=CHAT_SUSPEND) < datetime.now():
        response = {"Success": "False", "Error": "Chat suspended", }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    try:
        message = ChatMessage(user=user, room=room, text=message)
        message.save()
    except Exception, err:
        response = {"Success": "False", "Error": err, }
        return HttpResponse(json.dumps(response), mimetype="text/plain")

    response = {"Success": "True", }
    return HttpResponse(json.dumps(response), mimetype="text/plain")

