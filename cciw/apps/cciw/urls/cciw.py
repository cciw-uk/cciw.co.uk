from django.conf.urls.defaults import *

urlpatterns = patterns('cciw.apps.cciw.views.camps',
	(r'^camps/$', 'index'),
	(r'^camps/(?P<year>\d{4})/?$', 'yearindex'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/?$', 'detail')
)
