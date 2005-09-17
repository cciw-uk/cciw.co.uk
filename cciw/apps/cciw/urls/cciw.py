from django.conf.urls.defaults import *

urlpatterns = patterns('cciw.apps.cciw.views',
	(r'^members/$', 'members.index'),
	(r'^members/(?P<userName>[A-Za-z0-8_]+)/$', 'members.detail'),
	(r'^thisyear/$', 'camps.thisyear'),
	(r'^camps/$', 'camps.index'),
	(r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
	(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/?$', 'camps.detail'),
	(r'^sites/$', 'sites.index'),
	(r'^sites/(?P<name>.*)/$', 'sites.detail'),
	(r'', 'htmlchunk.find')
)
