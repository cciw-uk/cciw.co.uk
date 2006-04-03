from django.conf.urls.defaults import patterns

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
)
