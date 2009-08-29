from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import cciw.officers.views

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Plug in the password reset views
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset'),
    (r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
    # Normal views
    (r'^admin/', include(admin.site.urls), {'FORCESSL': True}),
    (r'^officers/', include('cciw.officers.urls'), {'FORCESSL': True})
)

if settings.DEBUG:
    urlpatterns = urlpatterns + patterns('',
      (r'^validator/', include('lukeplant_me_uk.django.validator.urls'))
    )

urlpatterns = urlpatterns + patterns('',
    (r'', include('cciw.cciwmain.urls'))
)
