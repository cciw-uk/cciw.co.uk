from django.conf.urls.defaults import *

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Override the admin for some views:
    (r'^admin/officers/application/add/$', 'cciw.officers.views.add_application'),
    (r'^admin/officers/application/([^/]+)/$', 'cciw.officers.views.change_application'),
    (r'^admin/password_reset/$', 'cciw.officers.views.password_reset'),
    (r'^admin/password_reset/done/$',  'cciw.officers.views.password_reset_done'),
    (r'^admin/password_reset/confirm/$', 'cciw.officers.views.password_reset_confirm'),
    # Normal views
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^officers/', include('cciw.officers.urls')),
    (r'^validator/', include('lukeplant_me_uk.django.validator.urls')),
    (r'', include('cciw.cciwmain.urls')),
)
