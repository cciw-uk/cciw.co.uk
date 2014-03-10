from django.conf.urls import patterns, url, include

urlpatterns = patterns('cciw.mail.views',
                       url(r'^show-list/(?P<address>.*)/$', 'show_list', name='cciw_mail_show_list'),
                   )
