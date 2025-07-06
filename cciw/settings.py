# isort:skip_file
import signal
import faulthandler
import json
import os
from datetime import timedelta
from pathlib import Path
import socket
import subprocess
import sys

hostname = socket.gethostname()


# resolve is important for removing symlinks, which can affect behaviour
basepath = Path(os.path.abspath(__file__)).resolve().parent.parent
parentpath = basepath.parent
SECRETS = json.load(open(basepath / "config" / "secrets.json"))

PROJECT_ROOT = basepath
HOME_PATH = Path(os.environ["HOME"]).resolve()
BASE_PATH = basepath

# We use `check --deploy` only from local development machine,
# to check deployment settings, so need to switch on that.
CHECK_DEPLOY = "manage.py check --deploy" in " ".join(sys.argv)
if CHECK_DEPLOY:
    LIVEBOX = True
    DEVBOX = False
else:
    LIVEBOX = hostname.startswith("cciw")
    DEVBOX = not LIVEBOX

TESTS_RUNNING = not LIVEBOX and "pytest" in sys.modules


if LIVEBOX and not CHECK_DEPLOY:
    LOG_PATH = HOME_PATH / "logs"  # See fabfile
else:
    LOG_PATH = parentpath / "logs"

if not LOG_PATH.exists():
    LOG_PATH.mkdir(parents=True)


BOGOFILTER_DIR = HOME_PATH / ".bogofilter-cciw"
if not BOGOFILTER_DIR.exists():
    BOGOFILTER_DIR.mkdir(parents=True)

if LIVEBOX:
    SECRET_KEY = SECRETS["PRODUCTION_SECRET_KEY"]
else:
    # We don't want any SECRET_KEY in a file in a VCS, and we also want the
    # SECRET_KEY to be to be the same as for production so that we can use
    # downloaded session database if needed.
    SECRET_KEY = SECRETS["PRODUCTION_SECRET_KEY"]


# == MISC ==

if DEVBOX:

    def show_toolbar(request):
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if is_ajax:
            return False
        if "-stats" in request.get_full_path():
            # debug toolbar slows down the stats pages for some reason
            return False
        if request.headers.get("Hx-Request", False):
            return False

        return True

    DEBUG = True
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": {"debug_toolbar.panels.redirects.RedirectsPanel"},
        "SHOW_TOOLBAR_CALLBACK": "cciw.settings.show_toolbar",
    }
else:
    DEBUG = False

USE_DEBUG_TOOLBAR = True

INTERNAL_IPS = ("127.0.0.1",)

LANGUAGE_CODE = "en-gb"

SITE_ID = 1
PRODUCTION_DOMAIN = "www.cciw.co.uk"

ROOT_URLCONF = "cciw.urls"

CACHES = (
    {
        "default": {
            # See also supervisor.conf.template
            "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
            "LOCATION": f'unix:{HOME_PATH / "cciw_memcached.sock"}',
            "KEY_PREFIX": "cciw.co.uk",
        }
    }
    if LIVEBOX
    else {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)


TIME_ZONE = "Europe/London"

USE_I18N = False
USE_TZ = True

LOGIN_URL = "/officers/"

ALLOWED_HOSTS = [".cciw.co.uk"]

if DEVBOX:
    ALLOWED_HOSTS.extend(["cciw.local", ".ngrok.io", ".ngrok-free.app"])

FIRST_PARTY_APPS = [
    "cciw.accounts",
    "cciw.cciwmain.apps.CciwmainConfig",
    "cciw.sitecontent",
    "cciw.officers",
    "cciw.utils",
    "cciw.bookings",
    "cciw.mail",
    "cciw.contact_us",
    "cciw.data_retention",
    "cciw.visitors",
]

INSTALLED_APPS = (
    [
        # 3rd party
        "django.contrib.auth",
        "cciw.apps.CciwAdminConfig",  # admin replacement
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.staticfiles",
        "django.forms",
        # Ours
    ]
    + FIRST_PARTY_APPS
    + [
        # 3rd party
        "django.contrib.messages",
        "paypal.standard.ipn",
        "django.contrib.humanize",
        "mptt",
        "sekizai",
        "sorl.thumbnail",
        "wiki",
        "wiki.plugins.attachments",
        "wiki.plugins.notifications",
        "wiki.plugins.images",
        "wiki.plugins.macros",
        "django_nyt",
        "compressor",
        "django_countries",
        "mailer",
        "captcha",
        "django_urlconfchecks",
        "spurl",
        "widget_tweaks",
        # Where we need to override something added:
        "cciw.overrides",
    ]
)

if DEVBOX and DEBUG:
    INSTALLED_APPS += [
        "django.contrib.admindocs",
    ]

if DEVBOX:
    INSTALLED_APPS += [
        "django_extensions",
    ]

if USE_DEBUG_TOOLBAR and DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]


SILENCED_SYSTEM_CHECKS = [
    "1_6.W001",
    "1_8.W001",
]

URLCONFCHECKS_SILENCED_VIEWS = {
    "debug_toolbar.panels.sql.views.sql_*": "E004",
    # CBVs:
    "*.View.as_view": "W001",
    # Django currently doesn't have type annotations:
    "django.*": "W003",
}

if not CHECK_DEPLOY:
    # It's annoying to have to fix data retention immediately
    SILENCED_SYSTEM_CHECKS.extend(
        [
            "dataretention.E002",
        ]
    )

DEFAULT_AUTO_FIELD = (
    "django.db.models.AutoField"  # to avoid warnings/migrations for existing 3rd party apps that haven't upgraded
)

# == AUTH ==

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "cciw.auth.CciwAuthBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    # See https://pages.nist.gov/800-63-3/sp800-63b.html#sec5
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "pwned_passwords_django.validators.PwnedPasswordsValidator",
    },
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

if LIVEBOX:
    # Can't use in development because we use HTTP locally
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
# CSRF_COOKIE_HTTPONLY = True   # Can't use this until we fix Javascript which requires checking all forms.

# == LOGGING ==

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        },
        "verbose": {"format": "%(levelname)s %(asctime)s %(name)s " "%(process)d %(thread)d %(message)s"},
    },
    "handlers": {
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "console": {
            "level": "DEBUG",
            "formatter": "verbose",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": LOG_PATH / "info_cciw_django.log",
            "maxBytes": 1000000,
            "backupCount": 5,
        },
        "paypal_debug": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": LOG_PATH / "paypal_debug_cciw_django.log",
            "maxBytes": 1000000,
            "backupCount": 5,
        },
        "aws_debug": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": LOG_PATH / "aws_debug_cciw_django.log",
            "maxBytes": 1000000,
            "backupCount": 5,
        },
        "mailer_runmailer": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": LOG_PATH / "runmailer_pg.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "paypal": {
            "level": "DEBUG",
            "handlers": ["paypal_debug"],
            "propagate": False,
        },
        "cciw.aws": {
            "level": "DEBUG",
            "handlers": ["aws_debug"],
            "propagate": False,
        },
        "mailer.postgres": {
            "handlers": ["mailer_runmailer"],
            "level": "DEBUG",
        },
        "mailer.engine": {
            "handlers": ["mailer_runmailer"],
            "level": "DEBUG",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
}

if DEVBOX:
    LOGGING["loggers"]["cciw"] = {
        "level": "INFO",
        "handlers": ["console"],
        "propagate": False,
    }
    LOGGING["root"]["handlers"] = ["console"]
    LOGGING["loggers"]["werkzeug"] = {
        "handlers": ["console"],
        "level": "DEBUG",
        "propagate": True,
    }

PASSWORD_RESET_TIMEOUT = 7 * 24 * 3600

# == DATABASE ==

if LIVEBOX and not CHECK_DEPLOY:
    DB_NAME = SECRETS["PRODUCTION_DB_NAME"]
    DB_USER = SECRETS["PRODUCTION_DB_USER"]
    DB_PASSWORD = SECRETS["PRODUCTION_DB_PASSWORD"]
    DB_PORT = SECRETS["PRODUCTION_DB_PORT"]
else:
    DB_NAME = "cciw_dev"
    DB_USER = "cciw_dev"
    DB_PASSWORD = "cciw_dev"
    DB_PORT = "5432"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "PORT": DB_PORT,
        "HOST": "localhost",
        "CONN_MAX_AGE": 30,
    }
}

# == STORAGE ==

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# == TEMPLATES ==

TEMPLATE_CONTEXT_PROCESSORS = [  # backwards compat for django-wiki
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.template.context_processors.media",
    "django.template.context_processors.static",
    "django.template.context_processors.request",
    "django.template.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "cciw.cciwmain.common.standard_processor",
    "sekizai.context_processors.sekizai",
] + ([] if not DEBUG else ["django.template.context_processors.debug"])

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            basepath / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": TEMPLATE_CONTEXT_PROCESSORS,
            "debug": DEBUG,
        },
    },
]

# == EMAIL ==

# Try to ensure we don't send real mail when testing.

# First step: set EMAIL_BACKEND correctly. This deals with mail sent via
# django's send_mail.


EMAIL_RECIPIENTS = SECRETS["EMAIL_RECIPIENTS"]
SERVER_EMAIL = "CCIW website <noreply@cciw.co.uk>"
DEFAULT_FROM_EMAIL = SERVER_EMAIL
ADMINS = [("webmaster", email) for email in EMAIL_RECIPIENTS["WEBMASTER"]]


if LIVEBOX:
    # We currently send using SMTP (amazon SES)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = SECRETS["SMTP_HOST"]
    EMAIL_PORT = SECRETS["SMTP_PORT"]
    EMAIL_HOST_USER = SECRETS["SMTP_USERNAME"]
    EMAIL_HOST_PASSWORD = SECRETS["SMTP_PASSWORD"]
    EMAIL_USE_TLS = SECRETS["SMTP_USE_TLS"]
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# django-mailer - used for some things where we need a queue. It is not used as
# default backend via EMAIL_BACKEND, but by calling mailer.send_mail explicitly,
# usally aliased as queued_mail.send_mail. We also can test this is being used
# e.g. in TestBaseMixin
MAILER_EMAIL_BACKEND = EMAIL_BACKEND

MAILER_USE_FILE_LOCK = False

EMAIL_ENCRYPTION_PUBLIC_KEYS = SECRETS["EMAIL_ENCRYPTION_PUBLIC_KEYS"]

if LIVEBOX:
    INCOMING_MAIL_DOMAIN = "cciw.co.uk"
else:
    # This separate domain makes development testing of AWS mail handling
    # easier:
    INCOMING_MAIL_DOMAIN = "mailtest.cciw.co.uk"


RECREATE_ROUTES_AUTOMATICALLY = LIVEBOX

# == AWS ==
if LIVEBOX:
    AWS_INCOMING_MAIL = SECRETS["AWS"]["INCOMING_MAIL"]
    AWS_CONFIG_USER = SECRETS["AWS"]["CONFIG"]
else:
    # Protect ourselves from accidentally using production AWS details in
    # development. When working on the SES integration code in development this
    # can be changed to same as above.
    AWS_INCOMING_MAIL = {}
    AWS_CONFIG_USER = {}

# == MAILING LISTS ==


# == SECURE DOWNLOADS ==

SECURE_DOWNLOAD_URL_BASE = "/protected/"  # See nginx conf

# == MIDDLEWARE ==

_MIDDLEWARE = [
    (DEVBOX and DEBUG, "cciw.db_debug.db_debug_middleware"),
    (True, "django.middleware.security.SecurityMiddleware"),
    (True, "django.middleware.gzip.GZipMiddleware"),
    (USE_DEBUG_TOOLBAR and DEBUG, "debug_toolbar.middleware.DebugToolbarMiddleware"),
    (True, "django.contrib.sessions.middleware.SessionMiddleware"),
    (True, "django.middleware.common.CommonMiddleware"),
    (True, "django.middleware.csrf.CsrfViewMiddleware"),
    (DEVBOX and DEBUG, "cciw.middleware.debug.debug_middleware"),
    (True, "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True, "django.contrib.messages.middleware.MessageMiddleware"),
    (True, "django.middleware.clickjacking.XFrameOptionsMiddleware"),
    (True, "cciw.middleware.auth.bad_password_checks"),
    (True, "cciw.middleware.auth.private_wiki"),
    (True, "cciw.bookings.middleware.booking_token_login"),
    (True, "cciw.middleware.threadlocals.thread_locals"),
]

MIDDLEWARE = tuple(val for (test, val) in _MIDDLEWARE if test)

# == MESSAGES ==

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

# == MEDIA ==

MEDIA_ROOT = parentpath / "usermedia"
STATIC_ROOT = parentpath / "static"

MEDIA_URL = "/usermedia/"
STATIC_URL = "/static/"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

COMPRESS_FILTERS = {
    "css": ["compressor.filters.css_default.CssAbsoluteFilter", "compressor.filters.cssmin.rCSSMinFilter"],
    "js": ["compressor.filters.jsmin.rJSMinFilter"] if LIVEBOX else [],
}
COMPRESS_PRECOMPILERS = []
COMPRESS_ENABLED = True

####################

# CCIW SPECIFIC SETTINGS AND CONSTANTS

# This 'from' email address is used on emails where the user
# might want to press 'reply' and get to a person e.g. for
# booking issues
WEBMASTER_FROM_EMAIL = "webmaster@cciw.co.uk"

BOOKING_FORMS_EMAILS = EMAIL_RECIPIENTS["BOOKING_FORMS"]
BOOKING_SECRETARY_EMAILS = EMAIL_RECIPIENTS["BOOKING_SECRETARY"]
GENERAL_CONTACT_EMAILS = EMAIL_RECIPIENTS["GENERAL_CONTACT"]
SECRETARY_EMAILS = EMAIL_RECIPIENTS["SECRETARY"]
WEBMASTER_EMAILS = EMAIL_RECIPIENTS["WEBMASTER"]
VOLUNTEERING_EMAILS = EMAIL_RECIPIENTS["VOLUNTEERING"]

BOOKINGFORMDIR = "downloads"

ESV_KEY = "IP"
DBS_VALID_FOR = 365 * 3  # We consider a DBS check valid for 3 years
ROLES_CONFIG_FILE = basepath / "config" / "static_roles.yaml"
DATA_RETENTION_CONFIG_FILE = basepath / "config" / "data_retention.yaml"

# Referenced from style.css
COLORS_CSS_DIR = "cciw/cciwmain/static/"
COLORS_CSS_FILE = "css/camp_colors.css"


# == Bookings ==
BOOKING_EMAIL_VERIFY_TIMEOUT = timedelta(days=3)  # See also payments_due_email.txt if changing this
BOOKING_SESSION_TIMEOUT = timedelta(weeks=2)
BOOKING_FULL_PAYMENT_DUE = timedelta(days=90)
BOOKING_FULL_PAYMENT_DUE_DISPLAY = "3 months"
BOOKING_EMAIL_REMINDER_FREQUENCY = timedelta(days=3)
LATE_BOOKING_THRESHOLD = timedelta(days=14)


# == DBS ==

# This should be a dictionary with 'name', 'email' and 'organisation' keys:
EXTERNAL_DBS_OFFICER = SECRETS["EXTERNAL_DBS_OFFICER"]


# == Third party ==

# Wiki
WIKI_ATTACHMENTS_EXTENSIONS = [
    "pdf",
    "doc",
    "odt",
    "docx",
    "txt",
    "svg",
    "png",
    "jpg",
    "jpeg",
]
WIKI_CHECK_SLUG_URL_AVAILABLE = False  # it checks it incorrectly for our situation

# Mailchimp
if LIVEBOX:
    MAILCHIMP_API_KEY = SECRETS["PRODUCTION_MAILCHIMP_API_KEY"]
    MAILCHIMP_NEWSLETTER_LIST_ID = SECRETS["PRODUCTION_MAILCHIMP_NEWSLETTER_LIST_ID"]
    MAILCHIMP_URL_BASE = SECRETS["PRODUCTION_MAILCHIMP_URL_BASE"]
else:
    MAILCHIMP_API_KEY = SECRETS["DEV_MAILCHIMP_API_KEY"]
    MAILCHIMP_NEWSLETTER_LIST_ID = SECRETS["DEV_MAILCHIMP_NEWSLETTER_LIST_ID"]
    MAILCHIMP_URL_BASE = SECRETS["DEV_MAILCHIMP_URL_BASE"]

# PayPal
if LIVEBOX:
    PAYPAL_TEST = False
    PAYPAL_RECEIVER_EMAIL = SECRETS["PRODUCTION_PAYPAL_RECEIVER_EMAIL"]
else:
    PAYPAL_TEST = True
    PAYPAL_RECEIVER_EMAIL = SECRETS["DEV_PAYPAL_RECEIVER_EMAIL"]

PAYPAL_BUY_BUTTON_IMAGE = "https://www.paypalobjects.com/en_US/GB/i/btn/btn_buynowCC_LG.gif"

# Sentry
if LIVEBOX and not CHECK_DEPLOY:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    version = subprocess.check_output(["git", "-C", BASE_PATH, "rev-parse", "HEAD"]).strip().decode("utf-8")
    release = "cciw@" + version

    sentry_sdk.init(
        dsn=SECRETS["PRODUCTION_SENTRY_CONFIG"]["dsn"],
        integrations=[DjangoIntegration()],
        release=release,
        traces_sample_rate=0.05,
        send_default_pii=True,
    )

# Captcha
CAPTCHA_FONT_PATH = str(BASE_PATH / "cciw" / "cciwmain" / "static" / "fonts" / "Monoton-Regular.ttf")

if not os.path.exists(CAPTCHA_FONT_PATH):
    raise ValueError(f"CAPTCHA_FONT_PATH is incorrect - file missing {CAPTCHA_FONT_PATH}")
CAPTCHA_FONT_SIZE = 45
CAPTCHA_LETTER_ROTATION = (-30, 30)


if TESTS_RUNNING:
    DATABASES["default"]["CONN_MAX_AGE"] = 0  # fix some deadlocks with DB flushing

    DEBUG = False
    TEMPLATE_DEBUG = False
    DEBUG_PROPAGATE_EXCEPTIONS = True

    PASSWORD_HASHERS = [
        "cciw.utils.tests.hashers.PlainPasswordHasher",
    ]

    MIDDLEWARE = [
        m
        for m in MIDDLEWARE
        if m not in ["debug_toolbar.middleware.DebugToolbarMiddleware", "cciw.middleware.debug.debug_middleware"]
    ]

    INSTALLED_APPS = [x for x in INSTALLED_APPS if x not in ["debug_toolbar"]]

    SEND_BROKEN_LINK_EMAILS = False

    ALLOWED_HOSTS = [
        "localhost",
    ]

    # If the process receives signal SIGUSR1, dump a traceback
    faulthandler.enable()
    faulthandler.register(signal.SIGUSR1)

    CAPTCHA_TEST_MODE = True
