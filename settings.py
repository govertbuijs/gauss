# Django settings for gauss project.
import os
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# XXX TODO Merge with Felix's code
DEV = False

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gauss',
        'USER': 'gauss',
        'PASSWORD': 'gauss',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
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
    'django.template.loaders.app_directories.load_template_source',
    #'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'gauss.urls'

TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates") )

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

#INTERNAL_IPS = ('127.0.0.1','255.255.255.255')

def custom_show_toolbar(bla):
    return True
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
}


