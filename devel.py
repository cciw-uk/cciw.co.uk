# import this to enable interactive use of django and the cciw app
import sys
import os
#sys.path = sys.path + ['/home/luke/devel/django/magic-removal', '/home/httpd/www.cciw.co.uk/django/',]
sys.path = sys.path + ['/home/luke/httpd/www.cciw.co.uk/django/','/home/luke/httpd/www.cciw.co.uk/django_src/', '/home/luke/local/lib/python2.4/site-packages/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings_calvin'
