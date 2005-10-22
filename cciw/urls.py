from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls.admin')),
    (r'', include('cciw.apps.cciw.urls')),
)
