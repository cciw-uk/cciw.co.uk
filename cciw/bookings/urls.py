from django.urls import path, re_path
from django.views.generic import RedirectView

from . import views
from .decorators import booking_account_optional

# The views mounted here relate only to end-user booking pages and
# functionality. Staff management of bookings is done in cciw.officers.views

urlpatterns = [
    path("", views.index, name="cciw-bookings-index"),
    path("start/", views.start, name="cciw-bookings-start"),
    path("email-sent/", views.email_sent, name="cciw-bookings-email_sent"),
    path("email-resent/", views.link_expired_email_sent, name="cciw-bookings-link_expired_email_sent"),
    path("v/", views.verify_and_continue, name="cciw-bookings-verify_and_continue"),
    path("verify-failed/", views.verify_email_failed, name="cciw-bookings-verify_email_failed"),
    re_path(
        r"^v/.+/$", booking_account_optional(RedirectView.as_view(pattern_name="cciw-bookings-verify_email_failed"))
    ),
    re_path(
        r"^p/.+/$", booking_account_optional(RedirectView.as_view(pattern_name="cciw-bookings-verify_email_failed"))
    ),
    path("account/", views.account_details, name="cciw-bookings-account_details"),
    path("loggedout/", views.not_logged_in, name="cciw-bookings-not_logged_in"),
    path("add-camper-details/", views.add_place, name="cciw-bookings-add_place"),
    path("edit-camper-details/<int:booking_id>/", views.edit_place, name="cciw-bookings-edit_place"),
    path("add-camper-details-reuse-data/", views.add_place_reuse_data, name="cciw-bookings-add_place_reuse_data"),
    path(
        "add-camper-details-reuse-data/<int:booking_id>/",
        views.add_place_reuse_data,
        name="cciw-bookings-add_place_reuse_data",
    ),
    path(
        "add-camper-details-use-previous-data-modal/",
        views.use_previous_data_modal,
        name="cciw-bookings-use_previous_data_modal",
    ),
    path(
        "add-camper-details-use-previous-data-modal/<int:booking_id>/",
        views.use_previous_data_modal,
        name="cciw-bookings-use_previous_data_modal",
    ),
    path("checkout/", views.list_bookings, name="cciw-bookings-list_bookings"),
    path("pay/", views.pay, name="cciw-bookings-pay"),
    path("pay/done/", views.pay_done, name="cciw-bookings-pay_done"),
    path("pay/cancelled/", views.pay_cancelled, name="cciw-bookings-pay_cancelled"),
    path("overview/", views.account_overview, name="cciw-bookings-account_overview"),
]
