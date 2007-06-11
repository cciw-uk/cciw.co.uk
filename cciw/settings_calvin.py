# Settings file for development box (calvin)

from settings_common import *

DEBUG = True
TEMPLATE_DEBUG = True

DATABASE_NAME = 'cciw_django'
DATABASE_USER = 'cciw'
DATABASE_PASSWORD = 'foo' 
DATABASE_HOST = ''        # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = 5433

basedir = r'/home/luke/httpd/www.cciw.co.uk/django'

# Absolute path to the directory that holds media.

MEDIA_ROOT =  basedir + '/media/'

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = 'http://cciw_django_local/media/'
SPECIAL_MEDIA_URL = 'http://cciw_django_local/sp_media/'
#MEDIA_URL = 'http://localhost:8000/media/'

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
#    "django.middleware.cache.CacheMiddleware",
#    "django.middleware.gzip.GZipMiddleware", # interferes with testing
    "lukeplant_me_uk.django.validator.middleware.ValidatorMiddleware",
#    "django.contrib.csrf.middleware.CsrfMiddleware", # interferes with testing
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)

INSTALLED_APPS = INSTALLED_APPS + (
    'lukeplant_me_uk.django.validator',
)

TEMPLATE_DIRS = (
    basedir + r'/templates/',
    r'/home/luke/httpd/www.cciw.co.uk/django_src/django/contrib/admin/templates/',
    basedir + r'/lukeplant_me_uk/django/validator/templates/',
    basedir + r'/lukeplant_me_uk/django/tagging/templates/',
)

FIXTURE_DIRS = [
    basedir + r'/cciw/cciwmain/fixtures/'
]
TEST_DIR = basedir + r'/cciw/cciwmain/tests/'

ADMIN_MEDIA_PREFIX = '/admin_media/'

CCIW_MEDIA_URL = MEDIA_URL

SEND_BROKEN_LINK_EMAILS = True

ESV_KEY = 'IP'
