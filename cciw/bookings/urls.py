from django.conf.urls.defaults import patterns, url

urlpatterns = \
    patterns('cciw.bookings.views',
             (r'^$', 'index'),
             (r'^start/$', 'start'),
             (r'^email-sent/$', 'email_sent'),
             (r'^v/(?P<account_id>[0-9A-Za-z]+)-(?P<token>.+)/$', 'verify_email'),
             )
