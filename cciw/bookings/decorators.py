from functools import wraps

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from .middleware import get_booking_account_from_request

_BOOKING_DECORATOR_APPLIED = "_BOOKING_DECORATOR_APPLIED"


def ensure_booking_account_attr(request):
    if not hasattr(request, "booking_account"):
        request.booking_account = get_booking_account_from_request(request)


def booking_account_required(view_func):
    """
    Requires a signed cookie that verifies the booking account,
    redirecting if this is not satisfied,
    and attaches the BookingAccount object as request.booking_account_required
    """

    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_account_attr(request)
        if request.booking_account is None:
            return HttpResponseRedirect(reverse("cciw-bookings-not_logged_in"))
        return view_func(request, *args, **kwargs)

    setattr(view, _BOOKING_DECORATOR_APPLIED, True)
    return view


def booking_account_optional(view_func):
    """
    Marks a view as not needing a booking account. It also adds
    `booking_account` to request object, though it might be be `None`
    """

    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_account_attr(request)
        return view_func(request, *args, **kwargs)

    setattr(view, _BOOKING_DECORATOR_APPLIED, True)
    return view


def check_booking_decorator(view_func):
    """
    Checks that one of the required decorators has been applied to the view function
    """
    # With this in place, we can more easily ensure that
    # `request.booking_account` exists (even if None) and ensure that we don't
    # forget to decorate views.
    if not getattr(view_func, _BOOKING_DECORATOR_APPLIED, False):
        raise AssertionError(
            f"{view_func} needs to have one of `booking_account_required`, `booking_account_optional` applied"
        )
    return view_func


# The following decorators depend on request.booking_account being present,
# meaning they depend on one of the previous required decorators.


def account_details_required(view_func):
    """
    Ensures that the user has filled out their account details. Otherwise
    redirects to that page.
    """

    @wraps(view_func)
    def view(request, *args, **kwargs):
        if not (request.booking_account is not None and request.booking_account.has_account_details()):
            return HttpResponseRedirect(reverse("cciw-bookings-account_details"))
        return view_func(request, *args, **kwargs)

    return view


def redirect_if_agreement_fix_required(view_func):
    """
    Ensure that any agreements have been fixed before continuing, redirecting to
    overview otherwise.

    """

    @wraps(view_func)
    def view(request, *args, **kwargs):
        if request.booking_account is not None and request.booking_account.bookings.agreement_fix_required().exists():
            messages.warning(
                request, "There is an issue with your existing bookings. Please address it before continuing."
            )
            return HttpResponseRedirect(reverse("cciw-bookings-account_overview"))
        return view_func(request, *args, **kwargs)

    return view
