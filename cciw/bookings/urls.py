from django.conf.urls.defaults import patterns, url

urlpatterns = \
    patterns('cciw.bookings.views',
             (r'^$', 'index'),
             (r'^start/$', 'start'),
             (r'^email-sent/$', 'email_sent'),
             (r'^v/(?P<account_id>[0-9A-Za-z]+)-(?P<token>.+)/$', 'verify_email'),
             (r'^v/failed/$', 'verify_email_failed'),
             (r'^account/$', 'account_details'),
             (r'^loggedout/$', 'not_logged_in'),
             (r'^add-place/$', 'add_place'),
             (r'^edit-place/(?P<id>\d+)/$', 'edit_place'),
             (r'^places-json/$', 'places_json'),
             (r'^checkout/$', 'list_bookings'),
             (r'^pay/$', 'pay'),
             (r'^pay/done/$', 'pay_done'),
             (r'^pay/cancelled/$', 'pay_cancelled'),
             )
