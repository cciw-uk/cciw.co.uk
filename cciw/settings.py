# Settings file
import os
import socket
import sys

hostname = socket.gethostname()

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../
parentdir = os.path.dirname(basedir)

DEVBOX = ('webfaction' not in hostname)
LIVEBOX = not DEVBOX

if LIVEBOX:
    from cciw.settings_priv import PRODUCTION, STAGING

WEBSERVER_RUNNING = 'mod_wsgi' in sys.argv

### MISC ###

from cciw.settings_priv import SECRET_KEY

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

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

ROOT_URLCONF = 'cciw.urls'

CACHE_BACKEND = 'dummy://'

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
    'cciw.utils',
    'django.contrib.messages',
    'mailer',
    'securedownload',
)

if not (LIVEBOX and WEBSERVER_RUNNING):
    # Don't want the memory overhead of these if we are serving requests
    INSTALLED_APPS += (
    'django.contrib.staticfiles',
    'south',
)

if DEVBOX and DEBUG:
    INSTALLED_APPS += (
        'django.contrib.admindocs',
        'output_validator',
        'debug_toolbar',
    )

if DEVBOX:
    INSTALLED_APPS += (
        'anonymizer',
)

######  DATABASE   ####

if DEVBOX:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'cciw',
            'USER': 'cciw',
            'PASSWORD': 'foo',
            'HOST': 'localhost',
            'PORT': 5432
            }
        }
else:
    from cciw.settings_priv import DATABASES

###### SESSIONS ########

if LIVEBOX and PRODUCTION:
    SESSION_COOKIE_SECURE = True

######  TEMPLATES  ###########

TEMPLATE_DIRS = (
    basedir + r'/templates',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    "cciw.cciwmain.common.standard_processor",
]

if DEBUG:
    TEMPLATE_CONTEXT_PROCESSORS.append("django.core.context_processors.debug")

#####  EMAIL  #######

if LIVEBOX:
    EMAIL_BACKEND = "mailer.backend.DbBackend"

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
    EMAIL_HOST = "smtp.webfaction.com"
    from cciw.settings_priv import EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

    SEND_BROKEN_LINK_EMAILS = False

##### MAILING LISTS ######

if LIVEBOX:
    from cciw.settings_priv import MAILBOX_PASSWORD, IMAP_MAIL_SERVER

##### WEBFACTION #####

if LIVEBOX:
    from cciw.settings_priv import WEBFACTION_PASSWORD, WEBFACTION_USER

##### SECUREDOWNLOAD #####

SECUREDOWNLOAD_SERVE_URL = "/file/"
SECUREDOWNLOAD_TIMEOUT = 3600

if DEVBOX:
    SECUREDOWNLOAD_SOURCE = os.path.join(parentdir, "resources/protected_downloads")
    SECUREDOWNLOAD_SERVE_ROOT = os.path.join(parentdir, "protected_downloads")
else:
    from cciw.settings_priv import SECUREDOWNLOAD_SOURCE, SECUREDOWNLOAD_SERVE_ROOT

### MIDDLEWARE_CLASSES ####

_MIDDLEWARE_CLASSES = (
    (DEVBOX,     "cciw.middleware.http.ActAsProxy"),
    (LIVEBOX,    "cciw.middleware.http.WebFactionFixes"),
    (LIVEBOX and PRODUCTION, "cciw.middleware.http.ForceSSLMiddleware"),
    (True,       "django.middleware.gzip.GZipMiddleware"),
#    (DEVBOX,     "debug_toolbar.middleware.DebugToolbarMiddleware"),
    (DEVBOX,     "output_validator.middleware.ValidatorMiddleware"),
    (True,       'django.middleware.csrf.CsrfViewMiddleware'),
    (True,       "django.contrib.sessions.middleware.SessionMiddleware"),
    (True,       "django.contrib.messages.middleware.MessageMiddleware"),
    (True,       "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True,       "django.middleware.common.CommonMiddleware"),
    (True,       "django.middleware.transaction.TransactionMiddleware"),
    (True,       "cciw.middleware.threadlocals.ThreadLocals"),
)

MIDDLEWARE_CLASSES = tuple([val for (test, val) in _MIDDLEWARE_CLASSES if test])

####### MESSAGES ##########

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

####### MEDIA #############

if DEVBOX:
    MEDIA_ROOT = os.path.join(parentdir, 'usermedia')
    STATIC_ROOT = os.path.join(parentdir, 'static')
else:
    # Need this to be relative to current. At the time this is used, the
    # directory above STATIC_ROOT will be one of many timestamped directories,
    # and we can't use the 'current' symlink.
    STATIC_ROOT = os.path.join(parentdir, 'static')
    from cciw.settings_priv import MEDIA_ROOT

MEDIA_URL = '/usermedia/'
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

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
FEEDBACK_EMAIL_TO = "feedback@cciw.co.uk"
BOOKINGFORMDIR = "downloads"
MEMBERS_PAGINATE_MESSAGES_BY = 20
WEBMASTER_EMAIL = "webmaster@cciw.co.uk"
LIST_MAILBOX_NAME = "camplists"
LIST_MAIL_DEBUG_ADDRESSES = [
    WEBMASTER_EMAIL
]
REFERENCE_CONCERNS_CONTACT_DETAILS = "Colin Davies on 029 20 617391 or Shirley Evans on 020 8569 0669."
ESV_KEY = 'IP'

if DEVBOX:
    OUTPUT_VALIDATOR_VALIDATORS = {
        'text/html': '/home/luke/httpd/myvalidate.sh',
        'application/xml+xhtml': '/home/luke/httpd/myvalidate.sh',
    }

    OUTPUT_VALIDATOR_IGNORE_PATHS = (
    )

    FIXTURE_DIRS = [
        basedir + r'/cciw/cciwmain/fixtures'
    ]
    TEST_DIR = basedir + r'/cciw/cciwmain/tests'

DEFAULT_CONTENT_TYPE = "text/html"

