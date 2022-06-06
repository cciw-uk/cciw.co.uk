import logging

import furl
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from cciw.bookings.email import EmailVerifyTokenGenerator, VerifyExpired, VerifyFailed, send_verify_email
from cciw.bookings.models import BookingAccount

BOOKING_COOKIE_SALT = "cciw.bookings.BookingAccount cookie"


logger = logging.getLogger(__name__)


def set_booking_account_cookie(response, account):
    response.set_signed_cookie(
        "bookingaccount", account.id, salt=BOOKING_COOKIE_SALT, max_age=settings.BOOKING_SESSION_TIMEOUT.total_seconds()
    )


def get_booking_account_from_request(request):
    cookie = request.get_signed_cookie(
        "bookingaccount",
        salt=BOOKING_COOKIE_SALT,
        default=None,
        max_age=settings.BOOKING_SESSION_TIMEOUT.total_seconds(),
    )
    if cookie is None:
        return None
    try:
        return BookingAccount.objects.get(id=cookie)
    except BookingAccount.DoesNotExist:
        return None


def unset_booking_account_cookie(response):
    response.delete_cookie("bookingaccount")


def booking_token_login(get_response):
    def middleware(request):
        if "bt" in request.GET:
            token = request.GET["bt"]
            verified_email = EmailVerifyTokenGenerator().email_from_token(token)
            if verified_email is VerifyFailed:
                logger.warning("Booking login verification failed, token=%s", token)
                return HttpResponseRedirect(reverse("cciw-bookings-verify_email_failed"))
            elif isinstance(verified_email, VerifyExpired):
                logger.warning("Booking login verification token expired, token=%s", token)
                EXPECTED_VIEWS = ["cciw-bookings-pay"]
                target_view_name = None
                for view_name in EXPECTED_VIEWS:
                    if reverse(view_name) == request.path:
                        target_view_name = view_name
                send_verify_email(request, verified_email.email, target_view_name=target_view_name)
                return HttpResponseRedirect(reverse("cciw-bookings-link_expired_email_sent"))
            elif isinstance(verified_email, str):
                try:
                    account = BookingAccount.objects.filter(email__iexact=verified_email)[0]
                except IndexError:
                    account = BookingAccount.objects.create(email=verified_email)

                # Redirect to the same URL, but with 'bt' removed. This helps to
                # stop the token being leaked (e.g. via the Referer header if
                # the page loads external resources).
                url = furl.furl(request.build_absolute_uri())
                resp = HttpResponseRedirect(url.remove(["bt"]).url)
                set_booking_account_cookie(resp, account)
                messages.info(
                    request,
                    f"Logged in as {account.email}! "
                    "You will stay logged in for two weeks. "
                    "Remember to log out if you are using a public computer.",
                )
                return resp

        return get_response(request)

    return middleware
