# Settings file for development box (calvin)

from settings_common import *

DEBUG = True
TEMPLATE_DEBUG = True

DATABASE_NAME = 'cciw_django'
DATABASE_USER = 'djangouser'
DATABASE_PASSWORD = 'foo' 
DATABASE_HOST = ''        # Set to empty string for localhost. Not used with sqlite3.

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/home/httpd/www.cciw.co.uk/django/media/'


# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = 'http://cciw_django_local/media/'

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
#    "django.middleware.cache.CacheMiddleware",
#    "django.middleware.gzip.GZipMiddleware",
    "lukeplant_me_uk.django.middleware.validator.ValidatorMiddleware",
    "lukeplant_me_uk.django.middleware.csrf.CsrfMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)

INSTALLED_APPS = INSTALLED_APPS + (
    'lukeplant_me_uk.django.apps.validator',
)

TEMPLATE_DIRS = (
    r'/home/httpd/www.cciw.co.uk/django/templates/',
    r'/home/httpd/www.cciw.co.uk/django_src/django/contrib/admin/templates/',
    r'/home/httpd/www.cciw.co.uk/django/lukeplant_me_uk/django/apps/validator/templates/',
#    r'/usr/lib/python2.4/site-packages/lukeplant_me_uk/django/apps/validator/templates/',
)

ADMIN_MEDIA_PREFIX = '/media/'

AWARD_UPLOAD_PATH = '/home/httpd/www.cciw.co.uk/django/media/images/awards'
MEMBERS_ICONS_UPLOAD_PATH = '/home/httpd/www.cciw.co.uk/django/media/images/members'
CCIW_MEDIA_URL = MEDIA_URL

SEND_BROKEN_LINK_EMAILS = False
