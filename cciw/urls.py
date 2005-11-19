from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls.admin')),
    (r'^validator/', include('lukeplant_me_uk.django.apps.validator.urls')),
    (r'', include('cciw.apps.cciw.urls')),
)
