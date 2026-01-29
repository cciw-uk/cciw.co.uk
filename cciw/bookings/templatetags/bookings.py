from django import template
from django.template.context import RequestContext
from django.urls import reverse

from cciw.bookings.views import BookingStage

register = template.Library()


@register.inclusion_tag("cciw/bookings/bookingbar.html", takes_context=True)
def bookingbar(context: RequestContext) -> dict[str, object]:
    request = context["request"]
    booking_account = request.booking_account
    logged_in = booking_account is not None
    current_stage = context["stage"]
    has_account_details = logged_in and request.booking_account.has_account_details()

    # Tuple of (name, caption, if this a link, url, message if inaccessible):
    msg_need_login = "Must be logged in to access this"
    msg_need_account_details = (
        "Need account details to access this" if logged_in else "Must be logged in to access this"
    )
    stages = [
        (
            BookingStage.ACCOUNT,
            "Account details",
            logged_in,
            reverse("cciw-bookings-account_details"),
            msg_need_login,
        ),
        (
            BookingStage.OVERVIEW,
            "Overview",
            logged_in,
            reverse("cciw-bookings-account_overview"),
            msg_need_login,
        ),
        (
            BookingStage.PLACE,
            (
                "Edit camper details"
                if current_stage == BookingStage.PLACE and "edit_mode" in context
                else "Add new booking"
            ),
            logged_in and has_account_details,
            reverse("cciw-bookings-add_place"),
            msg_need_account_details,
        ),
        (
            BookingStage.LIST,
            "Basket",
            logged_in and has_account_details,
            reverse("cciw-bookings-basket_list_bookings"),
            msg_need_account_details,
        ),
    ]
    return {
        "logged_in": logged_in,
        "request": request,
        "stages": stages,
        "current_stage": current_stage,
    }
