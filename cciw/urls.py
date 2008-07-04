from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import cciw.officers.views

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Override the admin for some views:
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset',
     dict(password_reset_form=cciw.officers.views.PasswordResetForm, 
          template_name='cciw/officers/password_reset_form.html',
          email_template_name='cciw/officers/password_reset_email.txt')),
    (r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done',
     dict(template_name='cciw/officers/password_reset_done.html')),
    (r'^reset/(?P<uid>\d+)-(?P<hash>\S{32})/$', 'cciw.officers.views.password_reset_confirm'),
    url(r'^reset/done/$', 'django.views.generic.simple.direct_to_template', 
        name='auth.password_reset_complete',
        kwargs={'template':'cciw/officers/password_reset_complete.html'}),
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
