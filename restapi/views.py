import uuid
import django
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.conf import settings
from djangorestframework.mixins import ResponseMixin
from djangorestframework.compat import View  # Use Django 1.3's django.views.generic.View, or fall back to a clone of that if Django < 1.3
from djangorestframework.renderers import DEFAULT_RENDERERS
from djangorestframework.renderers import JSONRenderer
from djangorestframework.response import Response
from djangorestframework import status


from django.forms.models import model_to_dict
from django.http import HttpResponse
from restapi.iphone import iPhone

from gauss.restapi.models import (Match, Magnet, MagnetComponent, User,
                                  Action, PushMessage)
from gauss.restapi.models import MATCH_SUGGESTION_CHOICES, get_value


Match.delete_old_matches()
#phone = iPhone()
##phone.get_feedback()
"""
Disclaimer: This code is work in progress, and meant for a concept-proof prototype
"""
def tail(f, n, offset=None):
    """Reads a n lines from f with an offset of offset lines.  The return
    value is a tuple in the form ``(lines, has_more)`` where `has_more` is
    an indicator that is `True` if there are more lines in the file.
    """
    avg_line_length = 74
    to_read = n + (offset or 0)

    while 1:
        try:
            f.seek(-(avg_line_length * to_read), 2)
        except IOError:
            # woops.  apparently file is smaller than what we want
            # to step back, go to the beginning instead
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            return lines[-to_read:offset and -offset or None], \
                   len(lines) > to_read or pos > 0
        avg_line_length *= 1.3

def help(request):
    from django.shortcuts import render_to_response
    
    return render_to_response('help.html')


def log(request):
    from django.shortcuts import render_to_response
    import commands
    #log = commands.getoutput('cat /root/django/gauss/screenlog.0')
    f = open('/root/django/gauss/screenlog.0', 'r')
    loglist = tail(f, 100)[0]
    #loglist = ['dfdsf', 'dsfsdf']
    del loglist[:1]
    loglist.reverse()
    loglist = [elem for elem in loglist if (elem.find('gausslog') < 0 and elem.find('CONTROL-C') < 0 and elem.find('DeprecationWarning') < 0 and elem.find('help') < 0)]

    log = '<p>' + '</p><p>'.join(loglist) + '</p>'
    return HttpResponse(log)
    


class UserView(ResponseMixin, View):
    """REST Interface for the User Class
    Uses djangorestframework's RendererMixin to provide support for multiple output formats.
    Methods:
    get(uid, uid2):
        has no real use yet
    post(uid):
        Add a new User (device)
    """
    renderers = [JSONRenderer]

    def get(self, request, uid, uid2):
        if uid!=uid2:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Access denied: can only see your own information"}))
        try:
            user = User.objects.get(device_id=uid)
            response = Response(200, {'Success': 'True',
                                      'creation_time': user.creation_time,
                                      'last_activity': user.last_activity,
                                      'latitude': user.pos_lat,
                                      'longitude': user.pos_long,})
        except:
            response = Response(200, {'Success': "False",
                                      'Error': "Can't find user",})

        return self.render(response)

class UserAdd(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid):
        user = User.objects.filter(device_id=uid)
        if user.count()==0:
            new= User(device_id=uid);
            new.save()
            try:
                new.full_clean()
            except ValidationError, e:
                return self.render(Response(200, {"Success": "False",
                                                  "Error": "Validation failed"}))
            #return Response(status.HTTP_200_CREATED)
            return self.render(Response(200, {"Success": "True",
                                              "newid": new.device_id}))
        else:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Nope"}))

class UserDelete(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))
        user.delete()
        return self.render(Response(200, {"Success": "True"}))
        
class UserDeleteAll(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))
        User.objects.all().delete()
        return self.render(Response(200, {"Success": "True"}))
        


class UserSetpos(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid, lat, long):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))

        user.set_position(lat, long)
        
        return self.render(Response(200, {"Success": "True"}))


class UserUpdate(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))

        for attribute in request.GET:
            try:
                user.__getattribute__(attribute)
            except AttributeError, e:
                error = "Invalid Attribute: %s" % attribute
                return self.render(Response(200, {"Success": "False",
                                                  "Error": error, }))
            value = request.GET[attribute]
            if value in ['0', 'false', 'False']:
                value = False
            elif value in ['1', 'true', 'True']:
                value = True

            user.__setattr__(attribute, value)

        user.save()
        return self.render(Response(200, {"Success": "True"}))


class MagnetList(ResponseMixin, View):
    """ REST interface for the Magnet Class
    Methods:
    get(uid):
        Returns the magnets a User currently has
    post(uid):
        Adds a new Magnet to a user.
        Creates a MATCH if somebody else already has this magnet (just for testing, will be replaced with range check-match later)
        Creates a new Magnet else.
    delete(uid):
        removes Magnet from User.
        Deletes it from DB if no other User has it
    """
    renderers = [JSONRenderer]
    #renderers = DEFAULT_RENDERERS

    def get(self, request, uid):
        #print [e.headline for e in Entry.objects.all()]
        magnets = Magnet.objects.filter(users=uid)
        if magnets.count()>=1:
            dict = {'Success':'True'}
            results = []
            for magnet in magnets:
                components = magnet.components.all()
                full =''
                subdict = {'id' : magnet.id}
                for component in components:
                    #dict.update({i : {component.order: component.name}})
                    subdict.update({component.order: component.name})
                    full += component.order
                
                results.append(subdict)
            dict.update({'Results': results})

            response = Response(200, dict)
        else:
            dict = {'Success':'False'}
            response = Response(200, dict)

        return self.render(response)

class MagnetAdd(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))
        # Are these truly 3 Components of the order 1,2 and 3?
        try:
            comp1 = MagnetComponent.objects.get(id=request.GET["comp1"])
            comp2 = MagnetComponent.objects.get(id=request.GET["comp2"])
            comp3 = MagnetComponent.objects.get(id=request.GET["comp3"])
        except LookupError, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Missing parameters"}))
        if not comp1.order=="1" or not comp2.order=="2" or not comp3.order=="3":
            error = "This is no valid Magnet; "\
                    "comp1 needs to be a Component of order 1, etc."
            return self.render(Response(200, {"Success": "False",
                                              "Error": error, }))

        # Is this combination unique?
        # If no, does the user already have this magnet?
        just_add_relation=False
        thismagnets = Magnet.objects.filter(
                components=comp1).filter(
                components=comp2).filter(
                components=comp3)

        otherUser=False
        if thismagnets.count()>0:
            for magnet in thismagnets:
                for x in magnet.users.iterator():
                    if x.device_id==uid:
                        error = "The User already has this magnet"
                        return self.render(Response(200, {"Success": "False",
                                                          "Error": error, }))
                    else:
                        # there is another user who has this magnet:
                        otherUser=x
                just_add_relation=True


        if not just_add_relation:
            new = Magnet()
            new.id = request.GET["comp3"]
            new.save()
            new.components=(comp1, comp2, comp3)
            new.users=(uid,)
            new.save()

            try:
                new.full_clean()
            except ValidationError, e:
                return self.render(Response(200, {"Success": "False",
                                                  "Error":"Validation failed"}))
            #return Response(status.HTTP_200_CREATED)
            return self.render(Response(200, {"Success": "True",
                                              "MagnetId": new.id}))
        else:
            magnet.users.add(uid)
            #TODO
            # Does another User have this magnet? if yes, initiate a Match:
            # (for testing, later a Match will only be
            # initiated only if the two users are within range)
            if otherUser:
                #maybe there is a match possible already?
                user.check_for_match()
                """
                print ("Initiate match")

                match = Match()
                match.magnet=magnet
                #match.place=""
                match.save()

                match.users=(uid, otherUser.device_id)
                match.initiate()


                return self.render(Response(200, {"Success": "True",
                                                  "MagnetId": magnet.id,
                                                  "Message": "Magnet added to User and Match initiated"}))
                """
            return self.render(Response(200, {"Success": "True",
                                              "MagnetId": magnet.id,
                                              "Message": "Magnet added to User"}))

class MagnetDelete(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid, magnetid):
        user = User.objects.get(device_id=uid)
        if magnetid == 'all':
            user.magnets.clear()
        else:
            user.magnets.remove(magnetid)

        # abort matching process if necessary:
        matches = user.matches.filter(magnet=magnetid).filter(status__lt=90)
        for match in matches:
            match.abort('92', user)
        return self.render(Response(200, {"Success": 'True',
                                              "Message": "deleted"}))
        """comp1 = MagnetComponent.objects.get(id=request.REQUEST["comp1"])
        comp2 = MagnetComponent.objects.get(id=request.REQUEST["comp2"])
        comp3 = MagnetComponent.objects.get(id=request.REQUEST["comp3"])
        
        magnet = Magnet.objects.filter(components=comp1).filter(components=comp2).filter(components=comp3).filter(users=uid)
        if magnet.count() >= 1:
            return self.render(Response(200, {"Success": "True",
                                              "Message": "Magnet removed from User" + magnet.count()}))
"""

class MagnetComponentView(ResponseMixin, View):
    """ REST interface for the Magnet Class
    Methods:
    get(uid, follows):
        A magnet consists of three components. The components are modeled as a directed graph:
        each Component can follow another component, or no component.
        The Components are used to fill the wheel selection menu in the iphone app.
        get(uid, 0) or get(uid) will get the Components for the first wheel,
        get(uid, <componentID>) will get the Components for the second wheel, according to what Component was chosen in the first one
    """
    renderers = [JSONRenderer]

    def get(self, request, uid, follows=False):
        #print [e.headline for e in Entry.objects.all()]
        if not(follows) or follows=="0":
            components = MagnetComponent.objects.filter(follows=None)
        else:
            components = MagnetComponent.objects.filter(follows=follows)
        
        if components.count()>=1:
            dict = {'Success':'True'}
            results = []

            for component in components:
                #dict.update({component.id : {'name': component.name}})
                results.append({'id' : component.id, 'name': component.name})
                
                #results.update({component.id : {'name': component.name}})
            dict.update({'Results': results})
            response = Response(200, dict)
        else:
            dict = {'Success':'False'}
            response = Response(200, dict)

        return self.render(response)


class MatchView(ResponseMixin, View):
    """ REST interface for the Match class
    Methods:
    get(uid):
        get the current Matches for a User.
        This API-Call will be initiated by the iPhone App every time it is started,
        to determine what the User has to do next (Suggest a connection method, or accept/decline a suggestion by the other user)
    """
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            thisUser = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))

        dict = {}
        results = []
        matches = thisUser.matches.exclude(status__gte=90)
        if matches.count()>=1:
            for match in matches:
                actions = match.actions.filter(user=thisUser).filter(done=False)
                if actions.count()>=1:
                    action = actions[0].name
                    actionId = actions[0].id
                else:
                    action = ''
                    actionId=''
                # What Buttons are to be shown in the app?
                if match.status == "1" or match.status=="3":
                    buttons = [{'key': 'ignore', 'label': 'Ignore'}]
                    choices = match.choices.split('|')

                    for choice in choices:
                        label = get_value(MATCH_SUGGESTION_CHOICES, choice)
                        buttons.append({'key': choice, 'label': label, })
                elif match.status =="2":
                    buttons = [ {'key': 'decline', 'label': 'Decline'},
                                {'key': 'accept', 'label': 'Accept'}]
                    choices = match.choices.split('|')
                    for choice in choices:
                        label = 'Suggest %s instead' % get_value(
                                            MATCH_SUGGESTION_CHOICES, choice)
                        buttons.insert(0, {'key': choice, 'label': label, })
                else:
                    buttons = []

                #User-specific Status:
                your_status = ''
                if match.status == '1':
                    your_status= 'makeSuggestion'
                elif match.status =='2' and action=='':
                    your_status= 'waitingForReply'
                elif match.status =='2' and action=='2':
                    your_status= 'suggestionReceived'
                elif match.status =='3' and action=='1':
                    your_status= 'makeNewSuggestion'
                elif match.status =='3' and action=='':
                    your_status= 'waitingForNewSuggestion'
                elif match.status =='4':
                    your_status= 'accepted'

                results.append({'id': match.id,
                                'wishid': match.magnet_id,
                                'wish': match.magnet.__unicode__(),
                                'your_status': your_status,
                                #'match_status': match.status,
                                'suggestion': match.suggestion,
                                'pendingactionid': actionId,
                                'pendingaction': action,
                                'buttons': buttons})
                dict.update({'Results': results})

        dict.update({'Success': 'True'})

        response = Response(200, dict)
        return self.render(response)

class MatchGetMeetingspot(ResponseMixin, View):
    renderers = [JSONRenderer]
    def get(self, request, uid, matchid):
        try:
            thisUser = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))


        match = Match.objects.filter(id=matchid).filter(users=uid)
        if match.count()==0:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid Match"}))
        match = match[0]
        dict = {'results' : match.get_meetingspot()}
        dict.update({'Success': 'True'})
        response = Response(200, dict)
        return self.render(response)


class ActionDo(ResponseMixin, View):
    """
    methods:
    post(uid, actionid):
        Called when a User wants to Complete a pending Action
        Will determine the current Status of the Match,
        and do whatever is necessary to complete the Action
    """
    renderers = [JSONRenderer]
    def get(self, request, uid, actionid):
        if not uid or not actionid:
            return self.render(Response(200, {"Success": "False",
                                             "Error": "Need more parameters"}))

        try:
            action = Action.objects.get(id=actionid)
            match = action.match
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Action not found"}))
        if action.done:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Action already done"}))

        if action.user.device_id!=uid:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Not your Action"}))

        #Get this User and the other User of the match:
        try:
            thisUser = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            return self.render(Response(200, {"Success": "False",
                                              "Error": "Invalid User"}))
        otherUser = False
        for user in match.users.all():
            if user.device_id != uid:
                otherUser = user
        if not otherUser:
            error = "The match is invalid: no 2nd User"
            return self.render(Response(200, {"Success": "False",
                                              "Error": error }))

        # suggestion needed?
        # If the User completes this action, it means he made a suggestion,
        # so he should have attached the needed parameters
        if action.name=='1':
            try:
                suggestion = request.GET['reply']
            except LookupError, e:
                return self.render(Response(200, {"Success": "False",
                                             "Error": "Need more parameters"}))

            # update match:
            if match.remove_choice(suggestion):
                #update Action(s):
                thisUser.complete_pending_actions(match)
                otherUser.clear_pending_actions(match)

                #more match updating:
                match.suggestion = suggestion
                match.status = '2'
                match.add_action('2', otherUser)
                match.save()

                # Push notification:
                message = 'SUGGESTION\n Another user wants '
                message += get_value(MATCH_SUGGESTION_CHOICES, suggestion)
                otherUser.push_message(message)
                return self.render(Response(200, {"Success": "True"}))
            else:
                return self.render(Response(200, {"Success": "False",
                                             "Error": "Suggestion not valid"}))

        # suggestion pending?
        # If the User completes this action,
        # it means a accepted or declined the suggestion
        elif action.name=='2':
            try:
                answer = request.GET['reply']
            except LookupError, e:
                error = "Need more parameters"
                return self.render(Response(200, {"Success": "False",
                                                  "Error": error, }))

            # what is the answer?
            if answer == 'accept':
                # update match
                suggestion = match.suggestion
                #match.suggestion=''
                match.status = '4'
                match.save()

                # update Actions
                thisUser.complete_pending_actions(match)
                otherUser.clear_pending_actions(match)

                # Push notification:
                message = 'MEET\n The other user accepts '
                message += get_value(MATCH_SUGGESTION_CHOICES, suggestion)
                otherUser.push_message(message)

                msg = "Accepted, other User notified"
                return self.render(Response(200, {"Success": "True",
                                                  "Message": msg, }))

            elif answer in match.choices.split('|'):
                # Decline and suggest something different?

                suggestion = answer
                # update match:
                if match.remove_choice(suggestion):

                    #update Action(s):
                    thisUser.complete_pending_actions(match)
                    otherUser.clear_pending_actions(match)

                    #more match updating:
                    match.suggestion= suggestion
                    match.status='2'
                    match.add_action('2', otherUser)
                    match.save()

                    message = 'COUNTER-SUGGESTION\n Another user rather wants '
                    message += get_value(MATCH_SUGGESTION_CHOICES, suggestion)
                    otherUser.push_message(message)

                    msg = "Declined and Suggestion posed, other User notified"
                    return self.render(Response(200, {"Success": "True",
                                                      "Message": msg, }))

                else:
                    return self.render(Response(200, {"Success": "False",
                                            "Error": "Suggestion not valid"}))


            elif answer=='decline':
                # Just Decline, no suggestion:
                # Is there a suggestion choice left?
                # if not, the Connection Process was a failure.
                if match.choices != '':
                    #update Actions:
                    thisUser.complete_pending_actions(match)
                    otherUser.clear_pending_actions(match)
                    # update match:
                    suggestion=match.suggestion
                    match.suggestion=''
                    match.status='3'
                    match.add_action('1', otherUser)
                    match.save()

                    message = 'DECLINED\n The other user does not want to '
                    message += get_value(MATCH_SUGGESTION_CHOICES, suggestion)
                    otherUser.push_message(message)

                    msg = "Declined, other User notified"
                    return self.render(Response(200, {"Success": "True",
                                                      "Message": msg}))
                # No Choice left:
                else:
                    #update Actions:
                    thisUser.complete_pending_actions(match)
                    otherUser.clear_pending_actions(match)
                    #update match:
                    suggestion=match.suggestion
                    #match.suggestion=''
                    match.abort('93', thisUser)

                    message = "Declined, no connection choice left -> aborted,"
                    message += " other User notified"
                    return self.render(Response(200, {"Success": "True",
                                                      "Message": message, }))

            else:
                return self.render(Response(200, {"Success": "False",
                                                  "Error": "Reply not valid"}))


class EchoView(ResponseMixin, View):
    """
    Api Call for iPhone Push notification testing
    """
    renderers = [JSONRenderer]
    def get(self, request, message, uid):
        user = User.objects.get(device_id=uid)

        from restapi.iphone import iPhone
        phone = iPhone()
        # ID of Arne's Gauss installation:
        #phone.udid='8bcf83a61e174bc0cb09280006801a845d52dd61d87aab6a74d54b44c941419a'
        phone.udid=uid
        if phone.send_message(message):
            return self.render(Response(200, {"Success": "True",
                                              "payload": phone.payload}))
        else:
            return self.render(Response(200, {"Success": "False"}))


class PushMessageView(ResponseMixin, View):
    """
    Displaying and deleting of fake push-messages
    """
    renderers = [JSONRenderer]
    def get(self, request, uid):
        try:
            user = User.objects.get(device_id=uid)
        except ObjectDoesNotExist, e:
            response = {"Success": "False", "Error": "Invalid User", }
            return self.render(Response(200, response))

        messages = []
        for message in PushMessage.objects.filter(user=user):
            messages.append({'id': message.id, 'message': message.message})
            # We need to display the messages only once
            message.delete()

        response = {"Success": "True", "Messages": messages, }
        return self.render(Response(200, response))

