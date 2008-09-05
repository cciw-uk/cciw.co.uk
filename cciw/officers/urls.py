from django.conf.urls.defaults import patterns

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
    (r'^applications/$', 'applications'),
    (r'^view_application/$', 'view_application'),
    (r'^leaders/$', 'leaders_index'),
    (r'^leaders/applications/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_applications'),
    (r'^leaders/references/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_references'),
    (r'^leaders/officer_list/(?P<year>\d{4})/(?P<number>\d+)/$', 'officer_list'),
)
