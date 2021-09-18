from django import template
from django.urls import reverse

from cciw.bookings.views import BookingStage, ensure_booking_account_attr

register = template.Library()


@register.inclusion_tag("cciw/bookings/bookingbar.html", takes_context=True)
def bookingbar(context):

    request = context['request']
    ensure_booking_account_attr(request)
    booking_account = request.booking_account
    logged_in = booking_account is not None
    current_stage = context['stage']
    has_account_details = logged_in and request.booking_account.has_account_details()

    # Tuple of (name, caption, if this a link, url, message if inaccessible):
    msg_need_login = 'Must be logged in to access this'
    msg_need_account_details = 'Need account details to access this' if logged_in else 'Must be logged in to access this'
    stages = [
        (BookingStage.LOGIN, 'Log in', False,
         '',
         'Go to "Overview" and use the "log out" link if you need to log in as someone else'),

        (BookingStage.ACCOUNT, 'Account details', logged_in,
         reverse('cciw-bookings-account_details'),
         msg_need_login),

        (BookingStage.OVERVIEW, 'Overview', logged_in,
         reverse('cciw-bookings-account_overview'),
         msg_need_login),

        (BookingStage.PLACE,
         'Edit camper details' if current_stage == BookingStage.PLACE and 'edit_mode' in context
         else 'Add new booking',
         logged_in and has_account_details,
         reverse('cciw-bookings-add_place'),
         msg_need_account_details),

        (BookingStage.LIST, 'Checkout', logged_in and has_account_details,
         reverse('cciw-bookings-list_bookings'),
         msg_need_account_details),

        (BookingStage.PAY, 'Pay', logged_in and has_account_details,
         reverse('cciw-bookings-pay'),
         msg_need_account_details),

    ]
    return {
        'logged_in': logged_in,
        'request': request,
        'stages': stages,
        'current_stage': current_stage,
    }
