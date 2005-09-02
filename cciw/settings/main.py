# Django settings for cciw project.

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

DATABASE_ENGINE = 'mysql' # 'postgresql', 'mysql', or 'sqlite3'.
DATABASE_NAME = 'cciw_django'             # Or path to database file if using sqlite3.
DATABASE_USER = 'djangouser'             # Not used with sqlite3.
DATABASE_PASSWORD = 'foo'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.

SITE_ID = 1

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = '__=9o22)i0c=ci+9u$@g77tvdsg9y-wu6v6#f4iott(@jgwig+'

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.middleware.doc.XViewMiddleware",
)

ROOT_URLCONF = 'cciw.settings.urls.main'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
)

INSTALLED_APPS = (
	'cciw.apps.cciw',
)
