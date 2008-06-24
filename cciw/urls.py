from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import cciw.officers.views

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Override the admin for some views:
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset',
     dict(password_reset_form=cciw.officers.views.PasswordResetForm, email_template_name='cciw/officers/password_reset_email.txt')),
    (r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', 
     dict(template_name='cciw/officers/password_reset_done.html')),
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
