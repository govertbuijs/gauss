import os
import sys

ROOT_DIR = os.path.abspath(os.path.split(__file__)[0])
ROOT_DIR = '/'.join(ROOT_DIR.split('/')[:-1])

activate_this = os.path.join(ROOT_DIR, 'bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

django_lib = 'lib/python2.6/site-packages/Django-1.3-py2.6.egg/django/'
sys.path.append( os.path.join(ROOT_DIR, django_lib) )

os.environ['DJANGO_SETTINGS_MODULE'] = 'gauss.settings'
os.environ['PYTHON_EGG_CACHE'] = os.path.join(ROOT_DIR, 'eggs')

if not ROOT_DIR in sys.path:
    sys.path.append(ROOT_DIR)
for item in os.listdir(ROOT_DIR):
    if not os.path.join(ROOT_DIR, item) in sys.path:
        sys.path.append( os.path.join(ROOT_DIR, item) )

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

import gauss.monitor
gauss.monitor.start(interval=1.0)
# Monitor non-python files
#monitor.track(os.path.join(os.path.dirname(__file__), 'site.cf'))
