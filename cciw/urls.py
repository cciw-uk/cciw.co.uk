from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import cciw.officers.views
import mailer.admin

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
    import django
    import os
    django_root = os.path.dirname(django.__file__)
    admin_media_root = django_root + '/contrib/admin/media'
    urlpatterns += patterns('',
                            (r'^validator/', include('lukeplant_me_uk.django.validator.urls')),
                            (r'^media/(?P<path>.*)$', 'django.views.static.serve',
                             {'document_root': settings.MEDIA_ROOT}),
                            (r'^sp_media/(?P<path>.*)$', 'django.views.static.serve',
                             {'document_root': settings.MEDIA_ROOT}),
    )

urlpatterns = urlpatterns + patterns('',
    (r'', include('cciw.cciwmain.urls'))
)
