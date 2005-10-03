# import this to enable interactive use of django and the cciw app
import sys
import os
sys.path = sys.path + ['/home/httpd/www.cciw.co.uk/django/','/home/httpd/www.cciw.co.uk/django_src/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings.main'
