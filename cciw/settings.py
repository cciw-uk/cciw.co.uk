# flake8: noqa

# Settings file
import os
import socket
import sys

hostname = socket.gethostname()

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../
parentdir = os.path.dirname(basedir)

PROJECT_ROOT = basedir
HOME_DIR = os.environ['HOME']

DEVBOX = ('webfaction' not in hostname)
LIVEBOX = not DEVBOX

if LIVEBOX:
    from cciw.settings_priv import PRODUCTION, STAGING, GOOGLE_ANALYTICS_ACCOUNT

from cciw.settings_priv import PAYPAL_TEST  # boolean indicating PayPal test mode
from cciw.settings_priv import PAYPAL_RECEIVER_EMAIL  # Email address of PayPal receiving account
from cciw.settings_priv import SECRET_KEY

WEBSERVER_RUNNING = 'mod_wsgi' in sys.argv
TESTS_RUNNING = 'test' in sys.argv

# == MISC ==

if DEVBOX:
    def show_toolbar(request):
        if request.is_ajax():
            return False
        if '-stats' in request.get_full_path():
            # debug toolbar slows down the stats pages for some reason
            return False
        return True

    DEBUG = True
    DEBUG_TOOLBAR_CONFIG = {
        'DISABLE_PANELS': set(['debug_toolbar.panels.redirects.RedirectsPanel']),
        'SHOW_TOOLBAR_CALLBACK': 'cciw.settings.show_toolbar',
    }
else:
    DEBUG = False

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

ROOT_URLCONF = 'cciw.urls'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:%s/memcached.sock' % HOME_DIR,
        'KEY_PREFIX': 'cciw.co.uk' if PRODUCTION else 'staging.cciw.co.uk'
    }
} if LIVEBOX else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


TIME_ZONE = "Europe/London"

USE_I18N = False
USE_TZ = True

LOGIN_URL = "/officers/"

ALLOWED_HOSTS = [".cciw.co.uk", "cciw.local"]

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.accounts',
    'cciw.cciwmain.apps.CciwmainConfig',
    'cciw.sitecontent',
    'cciw.officers',
    'cciw.utils',
    'cciw.bookings',
    'cciw.mail',
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
    'compressor',
    'django_countries',
    'opbeat.contrib.django',
    'anymail',
    'mailer',
]

if not (LIVEBOX and WEBSERVER_RUNNING):
    # Don't want the memory overhead of these if we are serving requests
    INSTALLED_APPS += [
        'django.contrib.staticfiles',
    ]

if DEVBOX and DEBUG:
    INSTALLED_APPS += [
        'django.contrib.admindocs',
        'debug_toolbar',
    ]


SILENCED_SYSTEM_CHECKS = [
    '1_6.W001',
    '1_8.W001',
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    'cciw.auth.CciwAuthBackend',
]

# == DATABASE ==

if DEVBOX:
    from cciw.settings_dev import DATABASES
else:
    from cciw.settings_priv import DATABASES

# == SESSIONS ==

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
)

# == TEMPLATES ==

TEMPLATE_CONTEXT_PROCESSORS = [  # backwards compat for django-wiki
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.media',
    'django.template.context_processors.static',
    'django.template.context_processors.request',
    'django.template.context_processors.tz',
    "django.contrib.messages.context_processors.messages",
    'cciw.cciwmain.common.standard_processor',
    'sekizai.context_processors.sekizai',
] + ([] if not DEBUG else ['django.template.context_processors.debug'])

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            basedir + r'/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': TEMPLATE_CONTEXT_PROCESSORS,
            'debug': DEBUG,
        },
    },
]

# == EMAIL ==

# Try to ensure we don't send mail via Mailgun when testing.

# First step: set EMAIL_BACKEND correctly. This deals with mail sent via
# django's send_mail.

# However, we also use Mailgun API directly. Rather than changing every
# reference to @cciw.co.uk, we patch up outgoing emails in cciw.mail.mailgun to
# use the sandbox domain.

if LIVEBOX and PRODUCTION:
    MAILGUN_DOMAIN = "cciw.co.uk"
else:
    from cciw.settings_priv import MAILGUN_SANDBOX_DOMAIN
    MAILGUN_DOMAIN = MAILGUN_SANDBOX_DOMAIN


SERVER_EMAIL = "CCIW website <website@cciw.co.uk>"
DEFAULT_FROM_EMAIL = SERVER_EMAIL
REFERENCES_EMAIL = "CCIW references <references@cciw.co.uk>"

if LIVEBOX and PRODUCTION:
    EMAIL_BACKEND = "anymail.backends.mailgun.MailgunBackend"
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# django-mailer - used for some things where we need a queue. It is not used as
# default backend via EMAIL_BACKEND, but by call mailer.send_mail explicitly.
MAILER_EMAIL_BACKEND = EMAIL_BACKEND

from cciw.settings_priv import MAILGUN_API_KEY
ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_API_KEY,
}

if TESTS_RUNNING:
    EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"
    MAILER_EMAIL_BACKEND = EMAIL_BACKEND

# == MAILING LISTS ==

if LIVEBOX:
    from cciw.settings_priv import MAILBOX_PASSWORD, IMAP_MAIL_SERVER

# == WEBFACTION ==

if LIVEBOX:
    from cciw.settings_priv import WEBFACTION_PASSWORD, WEBFACTION_USER
else:
    WEBFACTION_USER, WEBFACTION_PASSWORD = None, None

# == SECUREDOWNLOAD ==

SECUREDOWNLOAD_SERVE_URL = "/file/"
SECUREDOWNLOAD_TIMEOUT = 3600

if DEVBOX:
    SECUREDOWNLOAD_SOURCE = os.path.join(parentdir, "secure_downloads_src")
    SECUREDOWNLOAD_SERVE_ROOT = os.path.join(parentdir, "secure_downloads")
else:
    from cciw.settings_priv import SECUREDOWNLOAD_SOURCE, SECUREDOWNLOAD_SERVE_ROOT

# == MIDDLEWARE_CLASSES ==

_MIDDLEWARE_CLASSES = [
    (True,       "opbeat.contrib.django.middleware.OpbeatAPMMiddleware"),
    (LIVEBOX,    "cciw.middleware.http.WebFactionFixes"),
    (True,       "django.middleware.gzip.GZipMiddleware"),
    (DEVBOX,     "debug_toolbar.middleware.DebugToolbarMiddleware"),
    (True,       "django.contrib.sessions.middleware.SessionMiddleware"),
    (True,       "django.middleware.common.CommonMiddleware"),
    (True,       'django.middleware.csrf.CsrfViewMiddleware'),
    (DEVBOX and DEBUG, "cciw.middleware.debug.DebugMiddleware"),
    (True,       "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True,       "django.contrib.auth.middleware.SessionAuthenticationMiddleware"),
    (True,       "django.contrib.messages.middleware.MessageMiddleware"),
    (True,       'django.middleware.clickjacking.XFrameOptionsMiddleware'),
    (True,       "cciw.middleware.auth.PrivateWiki"),
    (True,       "cciw.bookings.middleware.BookingTokenLogin"),
    (True,       "cciw.middleware.threadlocals.ThreadLocals"),
]

DATABASE_ENGINE = 'postgresql'

MIDDLEWARE_CLASSES = tuple([val for (test, val) in _MIDDLEWARE_CLASSES if test])

# == MESSAGES ==

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

# == MEDIA ==

if DEVBOX:
    MEDIA_ROOT = os.path.join(parentdir, 'usermedia')
    STATIC_ROOT = os.path.join(parentdir, 'static')
else:
    from cciw.settings_priv import MEDIA_ROOT, STATIC_ROOT

MEDIA_URL = '/usermedia/'
STATIC_URL = '/static/'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

COMPRESS_PRECOMPILERS = [
    ('text/less', 'lessc {infile} {outfile}'),
]

####################

# CCIW SPECIFIC SETTINGS AND CONSTANTS

CONTACT_US_EMAIL = "feedback@cciw.co.uk"
BOOKING_SECRETARY_EMAIL = "bookings@cciw.co.uk"
BOOKING_FORM_EMAIL = "bookingforms@cciw.co.uk"
SECRETARY_EMAIL = "secretary@cciw.co.uk"
BOOKINGFORMDIR = "downloads"
WEBMASTER_EMAIL = "webmaster@cciw.co.uk"
LIST_MAILBOX_NAME = "camplists"
ESV_KEY = 'IP'
CRB_VALID_FOR = 365 * 3  # We consider a CRB valid for 3 years

# Referenced from style.less
COLORS_LESS_DIR = "cciw/cciwmain/static/"
COLORS_LESS_FILE = "css/camp_colors.less"


# == Bookings ==
BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS = 3
BOOKING_SESSION_TIMEOUT_SECONDS = 60 * 60 * 24 * 14  # 2 weeks
BOOKING_FULL_PAYMENT_DUE_DAYS = 3 * 30  # 3 months
BOOKING_EMAIL_REMINDER_FREQUENCY_DAYS = 3

DEFAULT_CONTENT_TYPE = "text/html"

BASE_DIR = basedir


# Third party

PAYPAL_IMAGE = "https://www.paypalobjects.com/en_US/GB/i/btn/btn_buynowCC_LG.gif"

WIKI_ATTACHMENTS_EXTENSIONS = [
    'pdf', 'doc', 'odt', 'docx', 'txt',
    'svg', 'png', 'jpg', 'jpeg',
]

# Mailchimp
from cciw.settings_priv import MAILCHIMP_API_KEY, MAILCHIMP_NEWSLETTER_LIST_ID, MAILCHIMP_URL_BASE

# Opbeat
from cciw.settings_priv import OPBEAT

if TESTS_RUNNING:
    os.environ['OPBEAT_DISABLE_SEND'] = 'true'
    OPBEAT = {}
