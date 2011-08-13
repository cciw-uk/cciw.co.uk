from django.conf.urls.defaults import patterns, url

urlpatterns = \
    patterns('cciw.bookings.views',
             (r'^$', 'index'),
             )
