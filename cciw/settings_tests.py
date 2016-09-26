# Settings file for testing on development box
from cciw.settings import *  # NOQA
from cciw.settings_priv import MAILGUN_TEST_RECEIVER  # NOQA


DATABASES['default']['CONN_MAX_AGE'] = 0  # fix some deadlocks with DB flushing

DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True

PASSWORD_HASHERS = [
    'django_plainpasswordhasher.PlainPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

MIDDLEWARE_CLASSES = [m for m in MIDDLEWARE_CLASSES
                      if m not in ["debug_toolbar.middleware.DebugToolbarMiddleware",
                                   "cciw.middleware.debug.DebugMiddleware"]
                      ]

INSTALLED_APPS = list(filter(lambda x: x not in [
    'debug_toolbar'
], INSTALLED_APPS))

SEND_BROKEN_LINK_EMAILS = False

TEST_DIR = basedir + r'/cciw/cciwmain/tests'


# Hack to disable migrations for tests, for speed
class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"

MIGRATION_MODULES = DisableMigrations()
