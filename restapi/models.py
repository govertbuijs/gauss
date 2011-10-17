from datetime import datetime, timedelta
from decimal import Decimal
from googlemaps import GoogleMaps
import json
from math import radians, sin, cos, atan2, sqrt
import urllib

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


# abort a match after inactivity of minutes:
MATCH_TIMEOUT = 1
# after a match has been aborted because of inactivity,
# how long before I can reinitiate it?
MATCH_QUARANTINE = 1

MATCH_STATUS_CHOICES = (
    ('0', 'enqueued'),
    ('1', 'new'),
    ('2', 'suggestion pending'),
    ('3', 'suggestion declined, waiting for new one'),
    ('4', 'suggestion accepted'),
    ('90', 'aborted by system - timeout'),
    ('92', 'aborted by user - magnet deleted'),
    ('93', 'aborted by user - declined last option'),
    ('94', 'aborted by user - used button')
)


ACTION_CHOICES = (
    ('', 'none'),
    ('1', 'suggest'),
    ('2', 'accept or decline suggestion')
)

MATCH_SUGGESTION_CHOICES =(
    ('meeting', 'Corner meeting'),
    ('facebook', 'Facebook connect'),
    ('chat', 'Chat direct'),
)

PLACE_TYPE_CHOICES =(
    ('gplaces', 'Google places'),
    ('intersection', 'Self-found intersection')
)

def get_value(dict, key):
    for x in dict:
        if x[0]==key:
            return x[1]


class User(models.Model):
    """
    The User stands for one IPhone device with a Gauss app installed.
    The device_id is the unique key that is generated by the APP for usage with the Apple Push Notification Service
    """
    device_id = models.CharField('Push Token', max_length=100, primary_key=True)
    creation_time = models.DateTimeField('date of creation', auto_now_add=True)
    last_activity = models.DateTimeField('Time of last activity', auto_now=True)
    pos_lat = models.DecimalField('Latitude', max_digits=9, decimal_places=6, default=0)
    pos_long = models.DecimalField('Longitude', max_digits=9, decimal_places=6, default=0)
    pos_time = models.DateTimeField('Time of the last position update', auto_now_add=True)
    auth_facebook = models.BooleanField('The User has Facebook auth', default=False)
    sandbox = models.BooleanField('The User uses the sandbox push server', default=False)


    def __unicode__(self):
        if self.device_id.__len__()>16:
            return self.device_id[0:15] + '...'
        else:
            return self.device_id

    def get_match(self):
        try:
            # not aborted and not enqueued:
            return self.matches.filter(status__lt=90).get(status__gt=0)
        except ObjectDoesNotExist, e:
            return False


    def push_message(self, message, match=False):
        from restapi.iphone import iPhone
        phone = iPhone()
        #Do we attach custom Parameters for the match?
        if match != False:
            try:
                action = match.actions.filter(user=self).get(done=False).name
            except ObjectDoesNotExist, e:
                action=''
            your_status=''
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
            elif match.status =='90':
                your_status= 'expired'
            elif match.status =='92' or match.status =='93' or match.status =='94':
                your_status= 'aborted'
            custom_params = {'matchId' : match.id,
                             'magnetId' : match.magnet.id,
                             'magnetName' : match.magnet.__unicode__(),
                             'status' : your_status}
        else:
            custom_params = {}

        #The User-Id is actually the Push udid:
        if self.device_id.__len__()>=5:
            phone.udid=self.device_id
            if not settings.DEV:
                phone.send_message(message, custom_params=custom_params, sandbox=self.sandbox)
        else:
            # OK, we don't have an iphone
            param_string = ', '.join([k+'='+str(v) for (k,v) in custom_params.items()])
            PushMessage(user=self, message=message, custom_params=param_string).save()

    def complete_pending_actions(self, match=False):
        if not match:
            actions = self.actions.filter(done=False)
        else:
            actions = self.actions.filter(done=False).filter(match=match)
        for action in actions:
            action.done=True
            action.save()

    def clear_pending_actions(self, match=False):
        if not match:
            actions = self.actions.filter(done=False)
        else:
            actions = self.actions.filter(done=False).filter(match=match)
        for action in actions:
            action.delete()

    def set_position(self, lat, long):

        self.pos_lat=Decimal(lat)
        self.pos_long=Decimal(long)
        self.pos_time=datetime.now()

        self.save()

        # set inactive Matches "aborted":
        Match.delete_old_matches()
        # Do we have a nearby match?
        self.check_for_match()

    def check_for_match(self):
        """
        Check if there is somebody with the same magnet within range.
        Initiate a Match object if yes.
        This method should by run by User.set_position()
        """

        #first of all check if we do not have a match running already:
        if self.get_match():
            return False

        # Range in Metres:
        range = Decimal('10000')
        # convert to lat/long degrees (approx):
        range_lat = Decimal(range / 111000)
        # todo: implement calculation by arc projection or other, better approximation
        # (current value is only correct for latitude of about 50)
        range_long = Decimal(range / 71000)

        # everybody within a square of range*2 side length:
        lat_min = self.pos_lat - range_lat
        lat_max = self.pos_lat + range_lat
        long_min = self.pos_long - range_long
        long_max = self.pos_long + range_long
        in_range = User.objects.filter(pos_lat__range=(lat_min, lat_max)).filter(pos_long__range=(long_min, long_max))
        #todo ... whose position is not obsolete:
        #in_range = in_range.filter(pos_time__gt=(datetime.now()-timedelta(hours=1)))
        # ... who is not this user:
        in_range = in_range.exclude(device_id=self.device_id)
        # ... who shares one of our magnets:
        soulmates = in_range.filter(magnets__in = self.magnets.all()).distinct()
        # ... who does not have a running match with this user already:
		# (not necessary as we may only have one match at a time anyway)
        #soulmates_unmatched = soulmates
        #for match in self.matches.exclude(status__gte=90):
        #    soulmates_unmatched = soulmates_unmatched.exclude(matches=match)
        #exclude the matches that timed out less than 60 minutes ago:
        #status:90 last_activity < jetzt-60m
        for match in self.matches.filter(status=90).exclude(last_activity__lt=(datetime.now()-timedelta(minutes=MATCH_QUARANTINE))):
            soulmates = soulmates.exclude(matches=match)
        # now trigger a matching Process for those guys:
        # actually only for one of them. later we should add some better priorization:
        matched = False
        for mate in soulmates.all():
        #if soulmates_unmatched.all().count()>=1:
        #    mate = soulmates_unmatched.all()[0]
            # does the other user already have a match?
            if mate.get_match():
                continue
            # get the shared magnets:

            magnets = Magnet.objects.filter(users=self).filter(users=mate)
            #soulmates = in_range.filter(magnets__in = self.magnets.all()).distinct()
            #search_users= [self, mate]
            #magnets = Magnet.objects.filter(users=self, users=mate)
            #if magnets.all().count()>=1:
            #cont = False
            for magnet in magnets.all():
                # do we already have a running match for this magnet? (not necessary as we may only have one match at a time anyway)
                #current_matches = self.matches.exclude(status__gte=90)
                #for current_match in current_matches:
                #    if current_match.magnet == magnet:
                #        cont = True
                #if cont:
                #    cont = False
                #    continue

                match = Match()
                #todo: do they share more than one magnet?
                match.magnet = magnet
                match.save()
                match.users=(self, mate)
                match.initiate()
                matched=True
                break
            if matched:
                break


class MagnetComponent(models.Model):
    """
    A magnet consists of three components. The components are modeled as a directed graph:
    each Component can follow another component, or no component.
    The Components are used to fill the wheel selection menu in the iphone app.
    "order" is the Position of the component in a magnet
    TODO: remodelling of "order" (not very elegant right now)
    """
    creation_time = models.DateTimeField('date of creation', auto_now_add=True)
    order = models.CharField(max_length=1)
    name = models.CharField(max_length=50)
    follows = models.ManyToManyField('self', symmetrical=False, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Magnet(models.Model):
    """
    A Magnet is a Combination of three MagnetComponents
    one ore more Users can have a Magnet
    """
    creation_time = models.DateTimeField('date of creation', 
            auto_now_add=True, auto_now=True)
    components = models.ManyToManyField(MagnetComponent)
    users = models.ManyToManyField(User, related_name='magnets')

    def __unicode__(self):
        return (self.components.get(order=3).name)


    class Meta:
        verbose_name = 'Magnet'
        verbose_name_plural = 'Magnets'
        #ordering = ['name']


class Place(models.Model):
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=15, choices=PLACE_TYPE_CHOICES)
    creation_time = models.DateTimeField('time of creation', auto_now_add=True)
    change_time = models.DateTimeField('time of last change', auto_now=True)
    icon = models.CharField(max_length=100)
    gp_reference = models.CharField('Google Places reference', max_length=255)
    gp_id = models.CharField('Google Places ID', max_length=50)
    pos_lat = models.DecimalField('Latitude', max_digits=13, decimal_places=10, default=0)
    pos_long = models.DecimalField('Longitude', max_digits=13, decimal_places=10, default=0)
    gp_types = models.CharField('Google Places Types', max_length=50)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return('http://maps.google.com/maps/place?cid=%s' % self.gp_id)


class Match(models.Model):
    """
    A Match is created when tho Users with the same magnet are within Range
    It is the central control Object for the interaction between those two Users
    Attributes:
    status:
        the current status in the lifecycle of the match
    choices:
        A comma seperated list of the connection options between the two users.
        Might be changed into a one-to-many relation in the future
    suggestion:
        if the status is '2':'suggestion pending', the current connection suggestion is stored here until the other User accepts or declines it.
    actions:
        the completed(done=True) and pending(done=False) Actions that are required of the Users
    """
    creation_time = models.DateTimeField('date of creation', auto_now_add=True)
    last_activity = models.DateTimeField('Time of last activity', auto_now=True)
    users = models.ManyToManyField(User, related_name='matches')
    magnet = models.ForeignKey(Magnet, related_name='matches')
    place = models.ForeignKey(Place, related_name='matches', null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=5, choices=MATCH_STATUS_CHOICES)
    choices = models.CharField(max_length=255)
    suggestion = models.CharField(max_length=20, choices=MATCH_SUGGESTION_CHOICES, blank=True)

    class Meta:
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'

    def __unicode__(self):
        user_list=[]
        for user in self.users.all():
            user_list.append(user.__unicode__())

        return (' + '.join(user_list) + ' like ' + self.magnet.__unicode__() + '(' + get_value(MATCH_STATUS_CHOICES, self.status) + ')')

    def initiate(self):
        """
        There is a new Match.
        Set the initial status, and send Notifications to the Users.
        This starts the User matching process.
        """
        # Add Choices:
        choices = []
        for choice in MATCH_SUGGESTION_CHOICES:
            # Facebook option only if both users are authed on FB
            if choice[0] == 'facebook':
                if filter(lambda x: not x.auth_facebook, self.users.all()):
                    continue
            # Chat option only if both users are webclient
            elif choice[0] == 'chat':
                if filter(lambda x: len(x.device_id) >= 5, self.users.all()):
                    continue
            choices.append(choice[0])
        self.choices = '|'.join(choices)

        #depr: does one of the user already have a running match?
        # if yes, enqueue this one:
        self.status = '1'
        #for user in self.users.all():
        #    if user.get_match():
        #        self.status='0'

        # Save
        self.save()

        if self.status=='1':
            self.initiate_users()

    def initiate_users(self):
        #Create actions and send Push notification to users:
        from restapi.iphone import iPhone
        phone = iPhone()
        for user in self.users.all():
            self.add_action('1', user)

            #send push notification:
            phone.udid=user.device_id
            message = self.magnet.__unicode__() + ': Match\n' + self.magnet.__unicode__()
            user.push_message(message, self)

    def add_action(self, action, user):
        new = Action()
        new.user = user
        new.match = self

        new.name = action
        new.done=False
        new.save()

    def remove_choice(self, choice):
        choicesList = self.choices.split('|')
        try:
            choicesList.remove(choice)
        except:
            return False

        if len(choicesList)>0:
            self.choices='|'.join (choicesList)
        else:
            self.choices=''
        return True


    def get_meetingspot(self):
        '''
        Find a spot for a corner meeting by calculating the route between the
        two users and using the middle(duration-wise) turn spot
        then we try to find a POI near that spot.
        Or maybe the other way around: using street corner as fallback.
        To be tested...
        '''
        user1 = self.users.all()[0]
        user2 = self.users.all()[1]

        Oppsite  = 20000
        lat1 = user1.pos_lat
        lat2 = user2.pos_lat
        lon1 = user1.pos_long
        lon2 = user2.pos_long

        dif_long = (lon1 + lon2)/2
        dif_lat = (lat1 + lat2)/2

        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = max(100, int(6371000 * c))

        # Increase the search radius for a place until something is found:
        # todo: implement fallback if there is no place anywhere near,
        # or the google places api does not work.
        result = []
        factor=0.15
        while result.__len__()==0 and factor<2:
            factor = factor + 0.15
            geo_args = {
               'location': str(dif_lat) + ',' + str(dif_long),
               'sensor': 'false',
               'radius': round(distance*factor),
               'types' : 'bar|bus_station|cafe|church|food|museum|' +
                         'night_club|restaurant|grocery_or_supermarket',
               'key': 'AIzaSyCEV7nPcE-n24T4Ncg6qC5bFEEqUqJ--lc'
            }

            base_url = 'https://maps.googleapis.com/maps/api/place/search/json'
            api_call_url = base_url + '?' + urllib.urlencode(geo_args)
            result = json.load(urllib.urlopen(api_call_url))
            result = result['results']

        if result.__len__()>0:
            result = result[0]
            query = Place.objects.filter(gp_id=result["id"])
            if query.all().count()==0:
                place = Place()
                place.name=result["name"]
                place.type='gplaces'
                place.icon=result["icon"]
                place.pos_lat=Decimal(str(result["geometry"]["location"]["lat"]))
                place.pos_long=Decimal(str(result["geometry"]["location"]["lng"]))
                place.gp_id = result["id"]
                place.gp_reference = result["reference"]
                place.gp_types='|'.join(result['types'])
                place.save()
                self.place=place
                self.save()
            else:
                place = query.all()[0]
                self.place=place
                self.save()


            return self.place
        else:
            return False

    def delete_old_matches():
        old = Match.objects.filter(last_activity__lt=(datetime.now()-timedelta(minutes=MATCH_TIMEOUT))).exclude(status__gte=90).all()
        for match in old:
            match.abort('90')
            

    delete_old_matches = staticmethod(delete_old_matches)

    def abort(self, code, user=False):
        code = str(code)
        self.status = code
        self.save()
        if code=='92':
            #get the other user, so we can send him a message:
            otherUser = self.get_other_user(user)
            otherUser.push_message(self.magnet.__unicode__() + ': Cancelled\n The other user deleted the magnet,', self)
        elif code=='93':
            #get the other user, so we can send him a message:
            otherUser= self.get_other_user(user)
            otherUser.push_message(self.magnet.__unicode__() + ': Cancelled\n The other user does not want to meet for %s.' % self.magnet.__unicode__(), self)
        if code=='90':
            #Match expired. notify both users:
            for user in self.users.all():
                user.push_message('The magnetism for %s has faded!' % self.magnet.__unicode__(), self)

        #Another match?
        for user in self.users.iterator():
            user.check_for_match()

    def get_other_user(self, user):
        for x in self.users.iterator():
            if x!=user:
                return x


class Action(models.Model):
    """
    Each time the Match-Process requires a action of a User, one Action object is created.
    Once the User completes the Action, it is set to done=True
    """
    creation_time = models.DateTimeField('time of creation', auto_now_add=True)
    change_time = models.DateTimeField('time of last change', auto_now=True)
    user = models.ForeignKey(User, related_name='actions')
    match = models.ForeignKey(Match, related_name='actions')
    name = models.CharField(max_length=5, choices=ACTION_CHOICES)
    done = models.BooleanField(default=False)

    def __unicode__(self):
        if self.done:
            done = 'done'
        else:
            done = 'pending'
        return self.user.__unicode__() + ' has to ' + get_value(ACTION_CHOICES, self.name) + ' (' + done + ')'


    class Meta:
        ordering = ['creation_time']

class PushMessage(models.Model):
    """
    Simple list to mimic the push-messages to non-iPhone devices (webclients)
    """
    user = models.ForeignKey(User)
    message = models.TextField()
    custom_params = models.TextField()
    creation_time = models.DateTimeField('time of creation', auto_now_add=True)
    change_time = models.DateTimeField('time of last change', auto_now=True)

class Feedback(models.Model):
    """
    User Feedback
    """
    user = models.ForeignKey(User)
    subject = models.CharField(max_length=150)
    body = models.TextField()
    creation_time = models.DateTimeField('date of creation', auto_now_add=True)