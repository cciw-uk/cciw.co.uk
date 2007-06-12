from django.conf.urls.defaults import patterns

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
    (r'^view_application/$', 'view_application_index'),
    (r'^view_application/(\d+)/$', 'view_application'),
)
