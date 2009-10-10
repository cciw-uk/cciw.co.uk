"""
Used by scripts to set up environment in context sensitive way,
so Django can be used
"""
import socket
import sys
import os

hostname = socket.gethostname()

if hostname == 'ryle':
    assert '/home/luke/.local/lib/python2.5/site-packages/' in os.environ['PYTHONPATH'].split(":")
    sys.path = sys.path + ['/home/luke/httpd/www.cciw.co.uk/current_src/','/home/luke/httpd/www.cciw.co.uk/django_src/', 
      '/home/luke/local/lib/python2.5/site-packages/', '/home/luke/devel/python/luke']
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings_calvin'
else:
    sys.path = sys.path + ['/home2/cciw/webapps/django_new/', '/home2/cciw/src/django/']
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
