from datetime import date

from django.conf import settings
from django.contrib.sites.models import get_current_site
from django.core import mail
from django.template import loader
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import int_to_base36, base36_to_int


class EmailVerifyTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the email verification
    mechanism.
    """
    def make_token(self, account):
        return self._make_token_with_timestamp(account, self._num_days(self._today()))

    def check_token(self, account, token):
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(account, ts), token):
            return False

        # Check the timestamp is within limit
        if (self._num_days(self._today()) - ts) > settings.BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, account, timestamp):
        # timestamp is number of days since 2011-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2131
        ts_b36 = int_to_base36(timestamp)

        key_salt = "cciw.bookings.EmailVerifyTokenGenerator"
        value = u"%s:%s:%s" % (account.id, account.email, timestamp)
        # We limit the hash to 20 chars to keep URL short
        hash = salted_hmac(key_salt, value).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)

    def _num_days(self, dt):
        return (dt - date(2011,1,1)).days

    def _today(self):
        # Used for mocking in tests
        return date.today()


def send_verify_email(request, booking_account):

    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain
    token_generator = EmailVerifyTokenGenerator()
    c = {
        'domain': domain,
        'account_id': int_to_base36(booking_account.id),
        'token': token_generator.make_token(booking_account),
        'protocol': 'https' if request.is_secure() else 'http',
        }

    body = loader.render_to_string("cciw/bookings/verification_email.txt", c)
    subject = "CCIW booking account"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [booking_account.email])


def check_email_verification_token(account, token):
    return EmailVerifyTokenGenerator().check_token(account, token)


def site_address_url_start():
    """
    Returns start of URL (protocol and domain) for this site
    (a guess)
    """
    protocol = 'https' if settings.SESSION_COOKIE_SECURE else 'http' # best guess
    return protocol + '://' + get_current_site(None).domain


def send_unrecognised_payment_email(ipn_obj):
    c = {
        'url_start': site_address_url_start(),
        'ipn_obj': ipn_obj,
        }

    body = loader.render_to_string("cciw/bookings/unrecognised_payment_email.txt", c)
    subject = "CCIW booking - unrecognised payment"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [settings.WEBMASTER_EMAIL])


def send_places_confirmed_email(bookings, **kwargs):
    if not bookings:
        return
    account = bookings[0].account
    if account.email == '':
        return

    c = {
        'url_start': site_address_url_start(),
        'account': account,
        'bookings': bookings,
        'payment_received': 'payment_received' in kwargs,
        }
    body = loader.render_to_string('cciw/bookings/place_confirmed_email.txt', c)
    subject = "CCIW booking - place confirmed"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])


def send_booking_expiry_mail(account, bookings, expired):
    if account.email == '':
        return

    c = {
        'url_start': site_address_url_start(),
        'account': account,
        'bookings': bookings,
        'expired': expired,
        }
    body = loader.render_to_string('cciw/bookings/place_expired_mail.txt', c)
    if expired:
        subject = "CCIW booking - booking expired"
    else:
        subject = "CCIW booking - booking expiry warning"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])
