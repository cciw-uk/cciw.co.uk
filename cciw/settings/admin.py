# Django settings for cciw project admin site.

from main import *

TEMPLATE_DIRS = (
    r'/home/httpd/www.cciw.co.uk/django/admin/templates',
    r'/home/httpd/www.cciw.co.uk/django_src/django/conf/admin_templates',
    r'/usr/lib/python2.4/site-packages/django/conf/admin_templates',
    # Put strings here, like "/home/html/django_templates".
)
ROOT_URLCONF = 'cciw.settings.urls.admin'
MIDDLEWARE_CLASSES = (
    'django.middleware.sessions.SessionMiddleware',
    'django.middleware.admin.AdminUserRequired',
    'django.middleware.common.CommonMiddleware',
)

ADMIN_FOR = ['cciw.settings.main']

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'
