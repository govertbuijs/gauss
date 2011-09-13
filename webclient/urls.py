from django.conf.urls.defaults import *

urlpatterns = patterns('gauss.webclient',
    url(r'^index.html', 'views.index', name="index", ),
)
