# Settings file for development box (calvin)
import os
from cciw.settings_common import *

DEBUG = True
TEMPLATE_DEBUG = True

DATABASE_NAME = 'cciw'
DATABASE_USER = 'cciw'
DATABASE_PASSWORD = 'foo'
DATABASE_HOST = ''        # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = 5433

basedir = os.path.dirname(os.path.abspath(os.path.dirname(__file__))) # ../
# Django source is in:
# ../django_src  or ../django_src_live
django_src = os.path.dirname(basedir) + os.path.basename(basedir).replace("current", "django")

# Absolute path to the directory that holds media.

MEDIA_ROOT =  basedir + '/media'

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = 'http://cciw_local/media'
SPECIAL_MEDIA_URL = 'http://cciw_local/sp_media'
#MEDIA_URL = 'http://localhost:8000/media/'

MIDDLEWARE_CLASSES = (
    "django.middleware.doc.XViewMiddleware",
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
    basedir + r'/templates',
)

FILE_UPLOAD_TEMP_DIR = basedir + "/uploads"

FIXTURE_DIRS = [
    basedir + r'/cciw/cciwmain/fixtures'
]
TEST_DIR = basedir + r'/cciw/cciwmain/tests'

ADMIN_MEDIA_PREFIX = '/admin_media/' # this requires trailing slash

CCIW_MEDIA_URL = MEDIA_URL

SEND_BROKEN_LINK_EMAILS = True

# For e-mail testing, run:
#  fakemail.py --path=/home/luke/httpd/www.cciw.co.uk/tests/mail --background
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None
EMAIL_PORT = 8025

ESV_KEY = 'IP'
