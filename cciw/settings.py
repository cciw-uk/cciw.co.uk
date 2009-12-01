# Settings file
import os
import socket
from cciw.settings_priv import SECRET_KEY, MAILBOX_PASSWORD, WEBFACTION_PASSWORD, WEBFACTION_USER, IMAP_MAIL_SERVER

hostname = socket.gethostname()

basedir = os.path.dirname(os.path.abspath(os.path.dirname(__file__))) # ../

DEVBOX = ('webfaction' not in hostname)

### MISC ###

if DEVBOX:
    DEBUG = True
    TEMPLATE_DEBUG = True
else:
    DEBUG = False
    TEMPLATE_DEBUG = False

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

CACHE_MIDDLEWARE_SECONDS = 200

ROOT_URLCONF = 'cciw.urls'

TIME_ZONE = "Europe/London"

USE_I18N = False

LOGIN_URL = "/officers/"

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.cciwmain',
    'cciw.officers',
    'cciw.tagging',
    'cciw.utils',
    'django.contrib.messages',
)

if DEBUG:
    INSTALLED_APPS += (
        'lukeplant_me_uk.django.validator',
        'debug_toolbar',
    )


######  DATABASE   ####
DATABASE_ENGINE = 'postgresql_psycopg2'

if DEVBOX:
    DATABASE_NAME = 'cciw'
    DATABASE_USER = 'cciw'
    DATABASE_PASSWORD = 'foo'
    DATABASE_HOST = ''        # Set to empty string for localhost. Not used with sqlite3.
    DATABASE_PORT = 5432
else:
    from cciw.settings_priv import DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST

######  TEMPLATES  ###########

TEMPLATE_DIRS = (
    basedir + r'/templates',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "cciw.cciwmain.common.standard_processor",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)

#####  EMAIL  #######
if DEVBOX:
    # For e-mail testing, run:
    #  fakemail.py --path=/home/luke/httpd/www.cciw.co.uk/tests/mail --background
    EMAIL_HOST = 'localhost'
    EMAIL_HOST_USER = None
    EMAIL_HOST_PASSWORD = None
    EMAIL_PORT = 8025

    SEND_BROKEN_LINK_EMAILS = True

else:
    SERVER_EMAIL = "website@cciw.co.uk"
    DEFAULT_FROM_EMAIL = SERVER_EMAIL
    EMAIL_HOST = "mail1.webfaction.com"
    from cciw.settings_priv import EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

    SEND_BROKEN_LINK_EMAILS = False

### MIDDLEWARE_CLASSES ####

_MIDDLEWARE_CLASSES = (
    (DEVBOX,     "cciw.middleware.http.DummyForceSSLMiddleware"),
    (not DEVBOX, "cciw.middleware.http.WebFactionFixes"),
    (not DEVBOX, "cciw.middleware.http.ForceSSLMiddleware"),
    (True,       "django.middleware.gzip.GZipMiddleware"),
#    (DEVBOX,     "lukeplant_me_uk.django.middleware.validator.ValidatorMiddleware"),
    (True,       'django.middleware.csrf.CsrfViewMiddleware'),
    (True,       "django.contrib.sessions.middleware.SessionMiddleware"),
    (True,       "django.contrib.messages.middleware.MessageMiddleware"),
    (True,       "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True,       "django.middleware.common.CommonMiddleware"),
    (True,       "cciw.middleware.threadlocals.ThreadLocals"),
)

MIDDLEWARE_CLASSES = tuple([val for (test, val) in _MIDDLEWARE_CLASSES if test])

####### MEDIA #############

# Absolute path to the directory that holds media.
MEDIA_ROOT = basedir + '/media'

# URL that handles the media served from MEDIA_ROOT.
if DEVBOX:
    MEDIA_URL = 'http://cciw_local/media'
    SPECIAL_MEDIA_URL = 'http://cciw_local/sp_media'
else:
    MEDIA_URL = '/media'
    SPECIAL_MEDIA_URL = '/sp_media'

FILE_UPLOAD_TEMP_DIR = basedir + "/uploads"

ADMIN_MEDIA_PREFIX = '/admin_media/'

CCIW_MEDIA_URL = MEDIA_URL

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

## CCIW SPECIFIC SETTINGS AND CONSTANTS
AWARD_UPLOAD_PATH = 'images/awards'
MEMBER_ICON_UPLOAD_PATH = 'images/members/temp'
MEMBER_ICON_PATH = 'images/members'
DEFAULT_MEMBER_ICON = 'defaultmember.gif'
MEMBER_ICON_MAX_SIZE = 48

CAMP_FORUM_RE = r'camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/'

FORUM_PAGINATE_POSTS_BY = 20
FORUM_PAGINATE_PHOTOS_BY = 20
FORUM_PAGINATE_TOPICS_BY = 30
ESV_BROWSE_URL = "http://www.gnpcb.org/esv/search/"
FEEDBACK_EMAIL_TO = "feedback@cciw.co.uk"
BOOKINGFORMDIR = "downloads"
MEMBERS_PAGINATE_MESSAGES_BY = 20
WEBMASTER_EMAIL = "webmaster@cciw.co.uk"
LIST_MAILBOX_NAME = "camplists"
LIST_MAIL_DEBUG_ADDRESSES = [
]
REFERENCE_CONCERNS_CONTACT_DETAILS = "Colin Davies on 029 20 617391 or Shirley Evans on 020 8569 0669."
ESV_KEY = 'IP'

if DEVBOX:
    VALIDATOR_APP_VALIDATORS = {
        'text/html': '/home/luke/httpd/myvalidate.sh',
        'application/xml+xhtml': '/home/luke/httpd/myvalidate.sh',
    }

    VALIDATOR_APP_IGNORE_PATHS = (
        '/admin/',
    )

    WEBFACTION_USER = None # stops any webfaction API calls being made.

    FIXTURE_DIRS = [
        basedir + r'/cciw/cciwmain/fixtures'
    ]
    TEST_DIR = basedir + r'/cciw/cciwmain/tests'

DEFAULT_CONTENT_TYPE = "application/xhtml+xml"
