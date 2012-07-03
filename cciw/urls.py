from autocomplete.views import autocomplete
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.views.generic.base import RedirectView

import cciw.auth
from cciw.bookings.models import BookingAccount

handler404 = 'cciw.cciwmain.views.handler404'

admin.autodiscover()

autocomplete.register(
    id='user',
    queryset=User.objects.all().order_by('first_name', 'last_name', 'email'),
    fields=('first_name__istartswith', 'last_name__istartswith'),
    limit=10,
    label=lambda user: u"%s %s <%s>" % (user.first_name, user.last_name, user.email),
    auth=lambda request: request.user.is_authenticated() and cciw.auth.is_camp_admin(request.user)
    )

autocomplete.register(
    id='account',
    queryset=BookingAccount.objects.all().order_by('name', 'post_code'),
    fields=('name__icontains',),
    limit=20,
    label=lambda acc: unicode(acc),
    auth=lambda request: request.user.is_authenticated and cciw.auth.is_booking_secretary(request.user)
    )

urlpatterns = patterns('',
    (r'^booking/', include('cciw.bookings.urls')),
    # Plug in the password reset views
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset'),
    (r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
    # Normal views
    (r'^admin/', include(admin.site.urls)),
    (r'^officers/', include('cciw.officers.urls')),
    url('^autocomplete/(\w+)/$', autocomplete, name='autocomplete'),
    (r'^wiki/', include('djiki.urls')),
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
