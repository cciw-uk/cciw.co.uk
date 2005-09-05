from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'', include('cciw.apps.cciw.urls.cciw')),
)
