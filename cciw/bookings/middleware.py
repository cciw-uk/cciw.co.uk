import furl
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from cciw.bookings.email import EmailVerifyTokenGenerator
from cciw.bookings.models import BookingAccount

BOOKING_COOKIE_SALT = 'cciw.bookings.BookingAccount cookie'


def set_booking_account_cookie(response, account):
    response.set_signed_cookie('bookingaccount', account.id,
                               salt=BOOKING_COOKIE_SALT,
                               max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)


def get_booking_account_from_request(request):
    cookie = request.get_signed_cookie('bookingaccount',
                                       salt=BOOKING_COOKIE_SALT,
                                       default=None,
                                       max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)
    if cookie is None:
        return None
    try:
        return BookingAccount.objects.get(id=cookie)
    except BookingAccount.DoesNotExist:
        return None


def unset_booking_account_cookie(response):
    response.delete_cookie('bookingaccount')


class BookingTokenLogin(object):
    def process_request(self, request):
        if 'bt' in request.GET:
            token = request.GET['bt']
            verified_email = EmailVerifyTokenGenerator().email_for_token(token)
            if verified_email is None:
                return HttpResponseRedirect(reverse('cciw-bookings-verify_email_failed'))
            else:
                try:
                    account = BookingAccount.objects.filter(email__iexact=verified_email)[0]
                except IndexError:
                    account = BookingAccount.objects.create(email=verified_email)

                # Redirect to the same URL, but with 'bt' removed. This helps to
                # stop the token being leaked (e.g. via the Referer header if
                # the page loads external resources).
                url = furl.furl(request.build_absolute_uri())
                resp = HttpResponseRedirect(url.remove(['bt']))
                set_booking_account_cookie(resp, account)
                messages.info(request, "Logged in! You will stay logged in for two weeks. Remember to log out if you are using a public computer.")
                return resp
