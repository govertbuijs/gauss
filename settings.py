# Django settings for gauss project.
import os
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

if PROJECT_ROOT.find('_dev')<0:
    DEV = False
else:
    DEV = True

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gauss_mvp',
        'USER': 'gauss',
        'PASSWORD': 'gauss',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "static_media")
MEDIA_URL = '/static_media/'
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'nyn4#sn53%1y5_sd-$i(zf!cjvj7m43q29$(gzfyv^5p5ml8g#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    #'django.template.loaders.filesystem.load_template_source',
    #'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.load_template_source',
    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

if DEV:
    ROOT_URLCONF = 'gauss_dev.urls'
else:
    ROOT_URLCONF = 'gauss.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates")
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'djangorestframework',

    'restapi',
    'webclient',
    'chat',
    #'debug_toolbar'
)

IPHONE_APN_PUSH_CERT = os.path.join(PROJECT_ROOT, "apns-dev.pem")
IPHONE_APN_PUSH_CERT_SANDBOX = os.path.join(PROJECT_ROOT, "apns-dev_sandbox.pem")
IPHONE_APN_PUSH_CERT_PROD = os.path.join(PROJECT_ROOT, "apns-dev_prod.pem")

#INTERNAL_IPS = ('127.0.0.1','255.255.255.255')

def custom_show_toolbar(bla):
    return True
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
}

MATCH_TIMEOUT = 30
MATCH_QUARANTINE = 60
MATCH_RANGE = 500

# Right now there is no "Matching Time" or "Interaction Time",
# just a timeout that is reset every time there one of the users does something.
# So if one user does something every 29 minutes, the match will never fade...
