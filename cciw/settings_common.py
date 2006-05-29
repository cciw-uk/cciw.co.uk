# Django settings for cciw project.
import cciw.cciwmain.utils


INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

DATABASE_ENGINE = 'postgresql'

SITE_ID = 1

SEND_BROKEN_LINK_EMAILS=True

# Make this unique, and don't share it with anybody.
SECRET_KEY = '__=9o22)i0c=ci+9u$@g77tvdsg9y-wu6v6#f4iott(@jgwig+'

CACHE_MIDDLEWARE_SECONDS = 200

CSRF_MIDDLEWARE_SECRET = SECRET_KEY

ROOT_URLCONF = 'cciw.urls'

VALIDATOR_APP_VALIDATORS = {
    'text/html': '/home/httpd/myvalidate.sh',
    'application/xml+xhtml': '/home/httpd/myvalidate.sh',
}

VALIDATOR_APP_IGNORE_PATHS = (
    '/admin/',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.cciwmain',
    'cciw.officers',
    'lukeplant_me_uk.django.tagging',
)

TIME_ZONE = "Europe/London"
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "cciw.cciwmain.common.standard_processor",
)

SERVER_EMAIL = "website@cciw.python-hosted.com"
DEFAULT_FROM_EMAIL = SERVER_EMAIL
EMAIL_HOST = "mail1.python-hosting.com"
EMAIL_HOST_USER = "cciw"
EMAIL_HOST_PASSWORD = "slarti"

## CCIW SPECIFIC SETTINGS AND CONSTANTS
AWARD_UPLOAD_PATH = 'images/awards'
MEMBERS_ICONS_UPLOAD_PATH = 'images/members'

THISYEAR = cciw.cciwmain.utils.ThisYear()
CAMP_FORUM_RE = r'camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/'

FORUM_PAGINATE_POSTS_BY = 20
FORUM_PAGINATE_PHOTOS_BY = 20
FORUM_PAGINATE_TOPICS_BY = 30

