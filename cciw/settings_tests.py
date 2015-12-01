# Settings file for testing on development box
from __future__ import unicode_literals

from cciw.settings import *  # NOQA

DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

PASSWORD_HASHERS = [
    'django_plainpasswordhasher.PlainPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

MIDDLEWARE_CLASSES = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.SessionAuthenticationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)

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
