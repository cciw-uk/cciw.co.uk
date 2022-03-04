# Settings file for testing on development box
import faulthandler
import signal
from datetime import timedelta

from cciw.settings_local import *  # NOQA
from cciw.settings_local import DATABASES, INSTALLED_APPS, MIDDLEWARE

DATABASES["default"]["CONN_MAX_AGE"] = 0  # fix some deadlocks with DB flushing

DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True

PASSWORD_HASHERS = [
    "django_plainpasswordhasher.PlainPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

MIDDLEWARE = [
    m
    for m in MIDDLEWARE
    if m not in ["debug_toolbar.middleware.DebugToolbarMiddleware", "cciw.middleware.debug.debug_middleware"]
]

INSTALLED_APPS = list(filter(lambda x: x not in ["debug_toolbar"], INSTALLED_APPS))

SEND_BROKEN_LINK_EMAILS = False

ALLOWED_HOSTS = [
    "localhost",
]


# Hack to disable migrations for tests, for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# If the process receives signal SIGUSR1, dump a traceback
faulthandler.enable()
faulthandler.register(signal.SIGUSR1)

CAPTCHA_TEST_MODE = True

# Use normal values of these for tests:
BOOKING_FULL_PAYMENT_DUE = timedelta(days=90)
BOOKING_FULL_PAYMENT_DUE_DISPLAY = "3 months"
LATE_BOOKING_THRESHOLD = timedelta(days=30)


TESTS_RUNNING = True
