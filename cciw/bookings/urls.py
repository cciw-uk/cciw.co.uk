from django.views.generic import RedirectView
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name="cciw-bookings-index"),
    url(r'^start/$', views.start, name="cciw-bookings-start"),
    url(r'^email-sent/$', views.email_sent, name="cciw-bookings-email_sent"),
    url(r'^v/$', views.verify_and_continue, name="cciw-bookings-verify_and_continue"),
    url(r'^verify-failed/$', views.verify_email_failed, name="cciw-bookings-verify_email_failed"),
    url(r'^v/.+/$', RedirectView.as_view(pattern_name="cciw-bookings-verify_email_failed")),
    url(r'^p/.+/$', RedirectView.as_view(pattern_name="cciw-bookings-verify_email_failed")),
    url(r'^account/$', views.account_details, name="cciw-bookings-account_details"),
    url(r'^loggedout/$', views.not_logged_in, name="cciw-bookings-not_logged_in"),
    url(r'^add-camper-details/$', views.add_place, name="cciw-bookings-add_place"),
    url(r'^edit-camper-details/(?P<id>\d+)/$', views.edit_place, name="cciw-bookings-edit_place"),
    url(r'^places-json/$', views.places_json, name="cciw-bookings-places_json"),
    url(r'^all-places-json/$', views.all_places_json, name="cciw-bookings-all_places_json"),
    url(r'^account-json/$', views.account_json, name="cciw-bookings-account_json"),
    url(r'^all-account-json/$', views.all_accounts_json, name="cciw-bookings-all_accounts_json"),
    url(r'^booking-problems-json/$', views.booking_problems_json, name="cciw-bookings-booking_problems_json"),
    url(r'^place-availability-json/$', views.place_availability_json, name="cciw-bookings-place_availability_json"),
    url(r'^expected-amount-json/$', views.get_expected_amount_due, name="cciw-bookings-get_expected_amount_due"),
    url(r'^checkout/$', views.list_bookings, name="cciw-bookings-list_bookings"),
    url(r'^pay/$', views.pay, name="cciw-bookings-pay"),
    url(r'^pay/done/$', views.pay_done, name="cciw-bookings-pay_done"),
    url(r'^pay/cancelled/$', views.pay_cancelled, name="cciw-bookings-pay_cancelled"),
    url(r'^overview/$', views.account_overview, name="cciw-bookings-account_overview"),

    # Autocomplete
    url(r'^bookingaccount-autocomplete/$',
        views.BookingAccountAutocomplete.as_view(), name='bookingaccount-autocomplete'),

]
