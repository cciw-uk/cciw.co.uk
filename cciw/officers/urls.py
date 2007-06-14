from django.conf.urls.defaults import patterns

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
    (r'^view_application/$', 'view_application'),
    (r'^leaders/applications/$', 'manage_applications'),
)
