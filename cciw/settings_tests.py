# Settings file for testing on development box
from cciw.settings import *  # NOQA
from cciw.settings import DATABASES, INSTALLED_APPS, MIDDLEWARE, basedir

DATABASES['default']['CONN_MAX_AGE'] = 0  # fix some deadlocks with DB flushing

DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True

PASSWORD_HASHERS = [
    'django_plainpasswordhasher.PlainPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

MIDDLEWARE = [m for m in MIDDLEWARE
              if m not in ["debug_toolbar.middleware.DebugToolbarMiddleware",
                           "cciw.middleware.debug.debug_middleware"]
              ]

INSTALLED_APPS = list(filter(lambda x: x not in [
    'debug_toolbar'
], INSTALLED_APPS))

SEND_BROKEN_LINK_EMAILS = False

TEST_DIR = basedir + r'/cciw/cciwmain/tests'

ALLOWED_HOSTS = [
    'localhost',
]

# Disable migrations for tests, for speed
app_names = [
    'accounts',
    'admin',
    'auth',
    'bookings',
    'cciwmain',
    'contenttypes',
    'django_nyt',
    'ipn',
    'mail',
    'mailer',
    'officers',
    'sessions',
    'sitecontent',
    'sites',
    'thumbnail',
    'wiki',
    'wiki_attachments',
    'wiki_images',
    'wiki_notifications'
]

MIGRATION_MODULES = {app: None for app in app_names}
