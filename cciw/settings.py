from __future__ import unicode_literals

# Settings file
import os
import socket
import sys

hostname = socket.gethostname()

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../
parentdir = os.path.dirname(basedir)

PROJECT_ROOT = basedir

DEVBOX = ('webfaction' not in hostname)
LIVEBOX = not DEVBOX

if LIVEBOX:
    from cciw.settings_priv import PRODUCTION, STAGING, GOOGLE_ANALYTICS_ACCOUNT

from cciw.settings_priv import PAYPAL_TEST # boolean indicating PayPal test mode
from cciw.settings_priv import PAYPAL_RECEIVER_EMAIL # Email address of PayPal receiving account
from cciw.settings_priv import SECRET_KEY

WEBSERVER_RUNNING = 'mod_wsgi' in sys.argv

### MISC ###

if DEVBOX:
    DEBUG = True
    TEMPLATE_DEBUG = True
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }
else:
    DEBUG = False
    TEMPLATE_DEBUG = False

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

ROOT_URLCONF = 'cciw.urls'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

TIME_ZONE = "Europe/London"

USE_I18N = False
USE_TZ = True

LOGIN_URL = "/officers/"

ALLOWED_HOSTS = [".cciw.co.uk"]

INSTALLED_APPS = (
    'autocomplete_light',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.cciwmain',
    'cciw.sitecontent',
    'cciw.forums',
    'cciw.officers',
    'cciw.utils',
    'cciw.bookings',
    'django.contrib.messages',
    'securedownload',
    'paypal.standard.ipn',
    'django.contrib.humanize',
    'mptt',
    'sekizai',
    'sorl.thumbnail',
    'wiki',
    'wiki.plugins.attachments',
    'wiki.plugins.notifications',
    'wiki.plugins.images',
    'wiki.plugins.macros',
    'django_nyt',
)

if not (LIVEBOX and WEBSERVER_RUNNING):
    # Don't want the memory overhead of these if we are serving requests
    INSTALLED_APPS += (
    'django.contrib.staticfiles',
    )

if DEVBOX and DEBUG:
    INSTALLED_APPS += (
        'django.contrib.admindocs',
        'debug_toolbar',
    )

if DEVBOX:
    INSTALLED_APPS += (
        'anonymizer',
)

if LIVEBOX and PRODUCTION:
    INSTALLED_APPS += (
    'mailer',
)


SILENCED_SYSTEM_CHECKS = [
    'admin.E202' # for BookingsManualPaymentInline
    ]
######  DATABASE   ####

if DEVBOX:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'cciw',
            'USER': 'cciw',
            'PASSWORD': 'foo',
            'HOST': 'localhost',
            'PORT': 5432,
            'CONN_MAX_AGE': 30,
            'ATOMIC_REQUESTS': True,
            }
        }
else:
    from cciw.settings_priv import DATABASES

###### SESSIONS ########

if LIVEBOX and PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
    'cciw.forums.hashers.CciwLegacyPasswordHasher', # for Member login only
)

######  TEMPLATES  ###########

TEMPLATE_DIRS = (
    basedir + r'/templates',
)

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.core.context_processors.debug",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    "cciw.cciwmain.common.standard_processor",
    "django.core.context_processors.tz",
    "sekizai.context_processors.sekizai",
]

if DEBUG:
    TEMPLATE_CONTEXT_PROCESSORS.append("django.core.context_processors.debug")

#####  EMAIL  #######

if LIVEBOX:
    if PRODUCTION:
        EMAIL_BACKEND = "mailer.backend.DbBackend"
    elif STAGING:
        EMAIL_BACKEND = "cciw.mail.backend.StagingBackend"

if DEVBOX:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # For more advanced e-mail testing which requires the exact email dumped to
    # a file, disable the above line and run:
    #  fakemail.py --path=/home/luke/devel/cciw.co.uk/tests/mail --background
    EMAIL_HOST = 'localhost'
    EMAIL_HOST_USER = None
    EMAIL_HOST_PASSWORD = None
    EMAIL_PORT = 8025

else:
    SERVER_EMAIL = "CCIW website <website@cciw.co.uk>"
    DEFAULT_FROM_EMAIL = SERVER_EMAIL
    EMAIL_HOST = "smtp.webfaction.com"
    from cciw.settings_priv import EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

##### MAILING LISTS ######

if LIVEBOX:
    from cciw.settings_priv import MAILBOX_PASSWORD, IMAP_MAIL_SERVER

##### WEBFACTION #####

if LIVEBOX:
    from cciw.settings_priv import WEBFACTION_PASSWORD, WEBFACTION_USER
else:
    WEBFACTION_USER, WEBFACTION_PASSWORD = None, None

##### SECUREDOWNLOAD #####

SECUREDOWNLOAD_SERVE_URL = "/file/"
SECUREDOWNLOAD_TIMEOUT = 3600

if DEVBOX:
    SECUREDOWNLOAD_SOURCE = os.path.join(parentdir, "secure_downloads_src")
    SECUREDOWNLOAD_SERVE_ROOT = os.path.join(parentdir, "secure_downloads")
else:
    from cciw.settings_priv import SECUREDOWNLOAD_SOURCE, SECUREDOWNLOAD_SERVE_ROOT

### MIDDLEWARE_CLASSES ####

_MIDDLEWARE_CLASSES = (
    (DEVBOX,     "cciw.middleware.http.ActAsProxy"),
    (LIVEBOX,    "cciw.middleware.http.WebFactionFixes"),
    (True,       "django.middleware.gzip.GZipMiddleware"),
    (DEVBOX,     "debug_toolbar.middleware.DebugToolbarMiddleware"),
    (True,       'django.middleware.csrf.CsrfViewMiddleware'),
    (True,       'django.middleware.clickjacking.XFrameOptionsMiddleware'),
    (True,       "django.contrib.sessions.middleware.SessionMiddleware"),
    (DEVBOX and DEBUG, "cciw.middleware.debug.DebugMiddleware"),
    (True,       "django.contrib.messages.middleware.MessageMiddleware"),
    (True,       "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True,       "django.middleware.common.CommonMiddleware"),
    (True,       "cciw.middleware.auth.PrivateWiki"),
    (True,       "cciw.middleware.threadlocals.ThreadLocals"),
)
DATABASE_ENGINE='postgresql'

MIDDLEWARE_CLASSES = tuple([val for (test, val) in _MIDDLEWARE_CLASSES if test])

####### MESSAGES ##########

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

####### MEDIA #############

if DEVBOX:
    MEDIA_ROOT = os.path.join(parentdir, 'usermedia')
    STATIC_ROOT = os.path.join(parentdir, 'static')
else:
    from cciw.settings_priv import MEDIA_ROOT, STATIC_ROOT

MEDIA_URL = '/usermedia/'
STATIC_URL = '/static/'

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

####################

## CCIW SPECIFIC SETTINGS AND CONSTANTS
AWARD_UPLOAD_PATH = 'images/awards'
MEMBER_ICON_UPLOAD_PATH = 'images/members/temp'
MEMBER_ICON_PATH = 'images/members'
DEFAULT_MEMBER_ICON = 'defaultmember.png'
MEMBER_ICON_MAX_SIZE = 48

CAMP_FORUM_RE = r'camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/'

FORUM_PAGINATE_POSTS_BY = 20
FORUM_PAGINATE_PHOTOS_BY = 20
FORUM_PAGINATE_TOPICS_BY = 30
FORUM_PAGINATE_NEWS_BY = 10
ESV_BROWSE_URL = "http://www.gnpcb.org/esv/search/"
CONTACT_US_EMAIL = "feedback@cciw.co.uk"
BOOKING_SECRETARY_EMAIL = "bookings@cciw.co.uk"
BOOKING_FORM_EMAIL = "bookingforms@cciw.co.uk"
BOOKINGFORMDIR = "downloads"
MEMBERS_PAGINATE_MESSAGES_BY = 20
WEBMASTER_EMAIL = "webmaster@cciw.co.uk"
LIST_MAILBOX_NAME = "camplists"
LIST_MAIL_DEBUG_ADDRESSES = [
    WEBMASTER_EMAIL
]
REFERENCE_CONCERNS_CONTACT_DETAILS = "Shirley Evans on 020 8569 0669."
ESV_KEY = 'IP'
CRB_VALID_FOR = 365 * 3 # We consider a CRB valid for 3 years

## Bookings ##
BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS = 3
BOOKING_SESSION_TIMEOUT_SECONDS = 60*60*24*14 # 2 weeks
BOOKING_FULL_PAYMENT_DUE_DAYS = 3 * 30 # 3 months
BOOKING_EMAIL_REMINDER_FREQUENCY_DAYS = 3

if DEVBOX:
    OUTPUT_VALIDATOR_VALIDATORS = {
        'text/html': '/home/luke/devel/myvalidate.sh',
        'application/xml+xhtml': '/home/luke/devel/myvalidate.sh',
    }

    OUTPUT_VALIDATOR_IGNORE_PATHS = (
    )


DEFAULT_CONTENT_TYPE = "text/html"

BASE_DIR = basedir

PAYPAL_IMAGE = "https://www.paypalobjects.com/en_US/GB/i/btn/btn_buynowCC_LG.gif"

WIKI_ATTACHMENTS_EXTENSIONS = [
    'pdf', 'doc', 'odt', 'docx', 'txt',
    'svg', 'png', 'jpg', 'jpeg',
]
