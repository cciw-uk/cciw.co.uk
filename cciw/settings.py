# Settings file for live environment
import os
from cciw.settings_common import *
from cciw.settings_priv import DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST

DEBUG = False
TEMPLATE_DEBUG = False

basedir = os.path.dirname(os.path.abspath(os.path.dirname(__file__))) # ../

# Absolute path to the directory that holds media.
MEDIA_ROOT = basedir + '/media'

# URL that handles the media served from MEDIA_ROOT.
MEDIA_URL = 'http://www.cciw.co.uk/media'
SPECIAL_MEDIA_URL = 'http://www.cciw.co.uk/sp_media'

MIDDLEWARE_CLASSES = (
    "cciw.middleware.http.WebFactionFixes",
#    "django.middleware.cache.CacheMiddleware",
    "django.middleware.gzip.GZipMiddleware",
#    "lukeplant_me_uk.django.middleware.validator.ValidatorMiddleware",
    'django.contrib.csrf.middleware.CsrfViewMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)


TEMPLATE_DIRS = (
    basedir + r'/templates',
)

FILE_UPLOAD_TEMP_DIR = basedir + "/uploads"

ADMIN_MEDIA_PREFIX = '/admin_media/'

CCIW_MEDIA_URL = MEDIA_URL

ESV_KEY = 'IP'

SEND_BROKEN_LINK_EMAILS = False
