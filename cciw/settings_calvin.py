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
MEDIA_ROOT = '/home/luke/httpd/www.cciw.co.uk/django/media/'


# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = 'http://cciw_django_local/media/'
#MEDIA_URL = 'http://localhost:8000/media/'

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
#    "django.middleware.cache.CacheMiddleware",
#    "django.middleware.gzip.GZipMiddleware",
    "lukeplant_me_uk.django.validator.middleware.ValidatorMiddleware",
    "django.contrib.csrf.middleware.CsrfMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)

INSTALLED_APPS = INSTALLED_APPS + (
    'lukeplant_me_uk.django.validator',
)

TEMPLATE_DIRS = (
    r'/home/luke/httpd/www.cciw.co.uk/django/templates/',
    r'/home/luke/httpd/www.cciw.co.uk/django_src/django/contrib/admin/templates/',
    r'/home/luke/httpd/www.cciw.co.uk/django/lukeplant_me_uk/django/validator/templates/',
    r'/home/luke/httpd/www.cciw.co.uk/django/lukeplant_me_uk/django/tagging/templates/',
)

ADMIN_MEDIA_PREFIX = '/admin_media/'

CCIW_MEDIA_URL = MEDIA_URL

SEND_BROKEN_LINK_EMAILS = False

ESV_KEY = 'TEST'
