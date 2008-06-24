from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Override the admin for some views:
    (r'^admin/password_reset/$', 'cciw.officers.views.password_reset'),
    (r'^admin/password_reset/done/$',  'cciw.officers.views.password_reset_done'),
    (r'^admin/password_reset/confirm/$', 'cciw.officers.views.password_reset_confirm'),
    # Normal views
    (r'^admin/(.*)', admin.site.root),
    (r'^officers/', include('cciw.officers.urls'))
)

if settings.DEBUG:
    urlpatterns = urlpatterns + patterns('',
      (r'^validator/', include('lukeplant_me_uk.django.validator.urls'))
    )

urlpatterns = urlpatterns + patterns('',
    (r'', include('cciw.cciwmain.urls'))
)
