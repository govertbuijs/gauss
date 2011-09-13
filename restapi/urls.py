from django.conf.urls.defaults import url, patterns

from gauss.restapi.views import (MagnetList, MagnetAdd, MagnetDelete, MatchView,
                                 MatchGetMeetingspot, UserView, UserAdd,
                                 UserDelete, UserDeleteAll, UserSetpos,
                                 UserUpdate, MagnetComponentView,
                                 MagnetComponentView, ActionDo,
                                 PushMessageView)


UID = '(?P<uid>[A-Za-z0-9_]*)'
UID2 = '(?P<uid2>[A-Za-z0-9_]*)'
MAGNET = '(?P<magnetid>[0-9al]*)'
MATCH = '(?P<matchid>[A-Za-z0-9_]*)'
LAT = '(?P<lat>[0-9/.]*)'
LON = '(?P<long>[0-9/.]*)'
ACTION = '(?P<actionid>[0-9]*)'
FOLLOWS = '(?P<follows>[0-9]+)'


urlpatterns = patterns('',
    url(r'^%s/wish/list/?$' % UID,
        MagnetList.as_view(), name='wish-list', ),

    url(r'^%s/wish/add/?$' % UID,
        MagnetAdd.as_view(), name='wish-add'),

    url(r'^%s/wish/delete/%s/?$' % (UID, MAGNET),
        MagnetDelete.as_view(), name='wish-delete'),


    url(r'^%s/match/list/?$' % UID,
        MatchView.as_view(), name='match-list'),

    url(r'^%s/match/getmeetingspot/%s/?$' % (UID, MATCH),
        MatchGetMeetingspot.as_view(), name='match-meetingspot'),


    url(r'^%s/user/get/%s/?$' % (UID, UID2),
        UserView.as_view(), name='user-view'),

    url(r'^%s/user/add/?$' % UID,
        UserAdd.as_view(), name='user-add'),

    url(r'^%s/user/delete/?$' % UID,
        UserDelete.as_view(), name='user-delete'),

    url(r'^%s/user/deleteall/?$' % UID,
        UserDeleteAll.as_view(), name='user-delete-all'),

    url(r'^%s/user/setpos/%s,%s/$' % (UID, LAT, LON),
        UserSetpos.as_view(), name='user-setpos'),

    url(r'^%s/user/update/?$' % UID,
        UserUpdate.as_view(), name='user-update'),


    url(r'^%s/wishcomponent/list/?$' % UID,
        MagnetComponentView.as_view(), name='component-view'),

    url(r'^%s/wishcomponent/list/%s/?$' % (UID, FOLLOWS),
        MagnetComponentView.as_view(), name='component-view-follows'),


    url(r'^%s/action/do/%s/?$' % (UID, ACTION),
        ActionDo.as_view(), name='action-do'),


    url(r'^%s/pushmessages/list/?$' % UID,
        PushMessageView.as_view(), name='push-message'),
)
