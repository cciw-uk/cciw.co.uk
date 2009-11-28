# Settings file for testing on development box

from cciw.settings import *

DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'

MIDDLEWARE_CLASSES = (
    "cciw.middleware.http.DummyForceSSLMiddleware",
    "django.middleware.common.CommonMiddleware",
#    "django.middleware.cache.CacheMiddleware",
#    "django.middleware.gzip.GZipMiddleware",
#    "lukeplant_me_uk.django.validator.middleware.ValidatorMiddleware",
#    "django.contrib.csrf.middleware.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "cciw.middleware.threadlocals.ThreadLocals",
)

INSTALLED_APPS = filter(lambda x: x != "lukeplant_me_uk.django.validator", INSTALLED_APPS)

SEND_BROKEN_LINK_EMAILS = False

