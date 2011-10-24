from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

from django.views.generic.simple import redirect_to
from django.views.static import serve


urlpatterns = patterns('',
    ('^$',              redirect_to, {'url': 'http://getgauss.com'}),

    (r'^admin/',        include(admin.site.urls)),
    (r'^admin/doc/',    include('django.contrib.admindocs.urls')),

    (r'^help/?$',       'restapi.views.help'),
    (r'^gausslog/?$',   'restapi.views.log'),

    (r'^webclient/',    include('gauss.webclient.urls')),
    (r'^chat/',         include('gauss.chat.urls')),
    (r'^',              include('gauss.restapi.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        (r'^static_media/(?P<path>.*)$', 'serve',
            { 'document_root': settings.MEDIA_ROOT, 'show_indexes': True }), )

