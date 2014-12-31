import autocomplete_light

from django.conf.urls import patterns, url, include
from django.conf import settings
from django.contrib import admin
from django_nyt.urls import get_pattern as get_nyt_pattern
from wiki.urls import get_pattern as get_wiki_pattern


handler404 = 'cciw.cciwmain.views.handler404'


autocomplete_light.autodiscover()


urlpatterns = patterns('',
    (r'^booking/', include('cciw.bookings.urls')),
    # Plug in the password reset views
    url(r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset', name="admin_password_reset"),
    url(r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', name="password_reset_done"),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm', name="password_reset_confirm"),
    url(r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete', name="password_reset_complete"),
    # Normal views
    (r'^admin/', include(admin.site.urls)),
    (r'^officers/', include('cciw.officers.urls')),
    url('^autocomplete/', include('autocomplete_light.urls')),
    (r'^notifications/', get_nyt_pattern()),
    (r'^wiki/', get_wiki_pattern()),
    (r'^paypal/ipn/', include('paypal.standard.ipn.urls')),
)

if settings.DEVBOX:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += patterns('',
                            (r'^admin_doc/', include('django.contrib.admindocs.urls')),
                            (r'^usermedia/(?P<path>.*)$', 'django.views.static.serve',
                             {'document_root': settings.MEDIA_ROOT}),
                            (r'^file/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve',
                             {'document_root': settings.SECUREDOWNLOAD_SERVE_ROOT}),
    )

    urlpatterns += staticfiles_urlpatterns()

urlpatterns = urlpatterns + patterns('',
    (r'', include('cciw.cciwmain.urls'))
)
