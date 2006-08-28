# Django settings for cciw project.

from settings_common_priv import SECRET_KEY, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, CSRF_MIDDLEWARE_SECRET

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

DATABASE_ENGINE = 'postgresql'

SITE_ID = 1

SEND_BROKEN_LINK_EMAILS=True

CACHE_MIDDLEWARE_SECONDS = 200

ROOT_URLCONF = 'cciw.urls'

VALIDATOR_APP_VALIDATORS = {
    'text/html': '/home/luke/httpd/myvalidate.sh',
    'application/xml+xhtml': '/home/luke/httpd/myvalidate.sh',
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

## CCIW SPECIFIC SETTINGS AND CONSTANTS
AWARD_UPLOAD_PATH = 'images/awards/'
MEMBER_ICON_UPLOAD_PATH = 'images/members/temp/'
MEMBER_ICON_PATH = 'images/members/'
DEFAULT_MEMBER_ICON = 'defaultmember.gif'
MEMBER_ICON_MAX_SIZE = 48

CAMP_FORUM_RE = r'camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/'

FORUM_PAGINATE_POSTS_BY = 20
FORUM_PAGINATE_PHOTOS_BY = 20
FORUM_PAGINATE_TOPICS_BY = 30
ESV_BROWSE_URL = "http://www.gnpcb.org/esv/search/"
FEEDBACK_EMAIL_TO = "L.Plant.98@cantab.net"
BOOKINGFORMDIR = "downloads"
MEMBERS_PAGINATE_MESSAGES_BY = 20
