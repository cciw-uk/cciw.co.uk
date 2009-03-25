# Django settings for cciw project.

from cciw.settings_common_priv import SECRET_KEY, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, CSRF_MIDDLEWARE_SECRET
from cciw.settings_common_priv import MAILBOX_PASSWORD, WEBFACTION_PASSWORD, WEBFACTION_USER, IMAP_MAIL_SERVER

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

DATABASE_ENGINE = 'postgresql_psycopg2'

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
    'django.contrib.csrf',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.cciwmain',
    'cciw.officers',
    'cciw.tagging',
    'cciw.utils',
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
    "django.contrib.csrf.context_processors.csrf",
    "cciw.cciwmain.common.standard_processor",
)

SERVER_EMAIL = "website@cciw.co.uk"
DEFAULT_FROM_EMAIL = SERVER_EMAIL
EMAIL_HOST = "mail1.webfaction.com"

USE_I18N = False

LOGIN_URL = "/officers/"

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

## CCIW SPECIFIC SETTINGS AND CONSTANTS
AWARD_UPLOAD_PATH = 'images/awards'
MEMBER_ICON_UPLOAD_PATH = 'images/members/temp'
MEMBER_ICON_PATH = 'images/members'
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
WEBMASTER_EMAIL = FEEDBACK_EMAIL_TO
LIST_MAILBOX_NAME = "camplists"
LIST_MAIL_DEBUG_ADDRESSES = [
]
