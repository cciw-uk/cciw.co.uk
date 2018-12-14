import django.contrib.auth.views
import django.contrib.staticfiles.views
import django.views.static
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django_nyt.urls import get_pattern as get_nyt_pattern
from wiki.urls import get_pattern as get_wiki_pattern

import cciw.officers.views

handler404 = 'cciw.cciwmain.views.handler404'


urlpatterns = [
    # Plug in the password reset views (before 'admin')
    url(r'^admin/password_reset/$', cciw.officers.views.cciw_password_reset, name="admin_password_reset"),
    url(r'^admin/password_reset/done/$', django.contrib.auth.views.password_reset_done, name="password_reset_done"),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', django.contrib.auth.views.password_reset_confirm, name="password_reset_confirm"),
    url(r'^reset/done/$', django.contrib.auth.views.password_reset_complete, name="password_reset_complete"),

    # Other 3rd party views
    url(r'^captcha/', include('captcha.urls')),
    url(r'^admin/', admin.site.urls),

    # Our normal views
    url(r'^booking/', include('cciw.bookings.urls')),
    url(r'^officers/', include('cciw.officers.urls')),
    url(r'^notifications/', get_nyt_pattern()),
    url(r'^wiki/', get_wiki_pattern()),
    url(r'^paypal/ipn/', include('paypal.standard.ipn.urls')),
    url(r'^mail/', include('cciw.mail.urls')),
]

if settings.DEVBOX:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    import debug_toolbar
    urlpatterns += [
        url(r'^usermedia/(?P<path>.*)$', django.views.static.serve,
            {'document_root': settings.MEDIA_ROOT}),
    ]

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        url(r'^django_functest/', include('django_functest.urls'))
    ]

    if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

urlpatterns = urlpatterns + [
    url(r'', include('cciw.cciwmain.urls'))
]
