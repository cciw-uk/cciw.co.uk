from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Concatenate

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .middleware import get_booking_account_from_request

if TYPE_CHECKING:
    from .models import BookingAccount

_BOOKING_DECORATOR_APPLIED = "_BOOKING_DECORATOR_APPLIED"


type ViewFunc = Callable[Concatenate[HttpRequest, ...], HttpResponse]


def ensure_booking_account_attr(request: HttpRequest):
    if not hasattr(request, "booking_account"):
        request.booking_account = get_booking_account_from_request(request)


def booking_account_required[**P](
    view_func: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """
    Requires a signed cookie that verifies the booking account,
    redirecting if this is not satisfied,
    and attaches the BookingAccount object as request.booking_account_required
    """

    @wraps(view_func)
    def view(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        ensure_booking_account_attr(request)
        booking_account: BookingAccount | None = request.booking_account
        if booking_account is None:
            return HttpResponseRedirect(reverse("cciw-bookings-not_logged_in"))
        return view_func(request, *args, **kwargs)

    setattr(view, _BOOKING_DECORATOR_APPLIED, True)
    return view


def booking_account_optional[**P](
    view_func: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """
    Marks a view as not needing a booking account. It also adds
    `booking_account` to request object, though it might be be `None`
    """

    @wraps(view_func)
    def view(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        ensure_booking_account_attr(request)
        return view_func(request, *args, **kwargs)

    setattr(view, _BOOKING_DECORATOR_APPLIED, True)
    return view


def check_booking_decorator[T: ViewFunc](view_func: T) -> T:
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


def account_details_required[**P](
    view_func: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """
    Ensures that the user has filled out their account details. Otherwise
    redirects to that page.
    """

    @wraps(view_func)
    def view(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        booking_account: BookingAccount | None = request.booking_account
        if not (booking_account is not None and booking_account.has_account_details()):
            return HttpResponseRedirect(reverse("cciw-bookings-account_details"))
        return view_func(request, *args, **kwargs)

    return view
