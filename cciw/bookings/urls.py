from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name="cciw.bookings.views.index"),
    url(r'^start/$', views.start, name="cciw.bookings.views.start"),
    url(r'^email-sent/$', views.email_sent, name="cciw.bookings.views.email_sent"),
    url(r'^v/(?P<account_id>[0-9A-Za-z]+)-(?P<token>.+)/$', views.verify_email_and_start, name="cciw.bookings.views.verify_email_and_start"),
    url(r'^p/(?P<account_id>[0-9A-Za-z]+)-(?P<token>.+)/$', views.verify_email_and_pay, name="cciw.bookings.views.verify_email_and_pay"),
    url(r'^v/failed/$', views.verify_email_failed, name="cciw.bookings.views.verify_email_failed"),
    url(r'^account/$', views.account_details, name="cciw.bookings.views.account_details"),
    url(r'^loggedout/$', views.not_logged_in, name="cciw.bookings.views.not_logged_in"),
    url(r'^add-camper-details/$', views.add_place, name="cciw.bookings.views.add_place"),
    url(r'^edit-camper-details/(?P<id>\d+)/$', views.edit_place, name="cciw.bookings.views.edit_place"),
    url(r'^places-json/$', views.places_json, name="cciw.bookings.views.places_json"),
    url(r'^all-places-json/$', views.all_places_json, name="cciw.bookings.views.all_places_json"),
    url(r'^account-json/$', views.account_json, name="cciw.bookings.views.account_json"),
    url(r'^all-account-json/$', views.all_accounts_json, name="cciw.bookings.views.all_accounts_json"),
    url(r'^booking-problems-json/$', views.booking_problems_json, name="cciw.bookings.views.booking_problems_json"),
    url(r'^place-availability-json/$', views.place_availability_json, name="cciw.bookings.views.place_availability_json"),
    url(r'^expected-amount-json/$', views.get_expected_amount_due, name="cciw.bookings.views.get_expected_amount_due"),
    url(r'^checkout/$', views.list_bookings, name="cciw.bookings.views.list_bookings"),
    url(r'^pay/$', views.pay, name="cciw.bookings.views.pay"),
    url(r'^pay/done/$', views.pay_done, name="cciw.bookings.views.pay_done"),
    url(r'^pay/cancelled/$', views.pay_cancelled, name="cciw.bookings.views.pay_cancelled"),
    url(r'^overview/$', views.account_overview, name="cciw.bookings.views.account_overview"),
]
