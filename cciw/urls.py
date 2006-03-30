from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    # Override the admin for some views:
    (r'^admin/officers/application/add/$', 'cciw.officers.views.add_application'),
    (r'^admin/officers/application/([^/]+)/$', 'cciw.officers.views.change_application'),
    # Normal views
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^officers/', include('cciw.officers.urls')),
    (r'^validator/', include('lukeplant_me_uk.django.apps.validator.urls')),
    (r'', include('cciw.cciwmain.urls')),
)
