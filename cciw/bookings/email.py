import base64
import binascii
from datetime import datetime, timedelta

import attr
import mailer as queued_mail
from django.conf import settings
from django.core import mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template import loader
from django.utils import timezone

from cciw.cciwmain import common
from cciw.officers.email import admin_emails_for_camp


class VerifyFailed:
    pass


VerifyFailed = VerifyFailed()


@attr.s
class VerifyExpired:
    email = attr.ib()


class EmailVerifyTokenGenerator:
    """
    Strategy object used to generate and check tokens for the email verification
    mechanism.
    """

    def __init__(self):
        self.signer = TimestampSigner(salt="cciw.bookings.EmailVerifyTokenGenerator")

    def token_for_email(self, email):
        """
        Returns a verification token for the provided email address
        """
        return self.url_safe_encode(self.signer.sign(email))

    def email_for_token(self, token, max_age=None):
        """
        Extracts the verified email address from the token, or a VerifyFailed
        constant if verification failed, or VerifyExpired if the link expired.
        """
        if max_age is None:
            max_age = settings.BOOKING_EMAIL_VERIFY_TIMEOUT
        try:
            unencoded_token = self.url_safe_decode(token)
        except (UnicodeDecodeError, binascii.Error):
            return VerifyFailed
        try:
            return self.signer.unsign(unencoded_token, max_age=max_age)
        except (SignatureExpired,):
            return VerifyExpired(self.signer.unsign(unencoded_token))
        except (BadSignature,):
            return VerifyFailed

    # Somehow the trailing '=' produced by base64 encode gets eaten by
    # people/programs handling the email verification link. Additional
    # trailing '=' don't hurt base64 decode. So we strip thenm when encoding,
    # and add them on decoding.
    # See also TestEmailVerifyTokenGenerator.

    def url_safe_encode(self, value):
        return base64.urlsafe_b64encode(value.encode("utf-8")).decode("utf-8").rstrip("=")

    def url_safe_decode(self, token):
        token = token + "=="
        return base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")


def send_verify_email(request, booking_account_email, target_view_name=None):
    if target_view_name is None:
        target_view_name = "cciw-bookings-verify_and_continue"
    c = {
        "domain": common.get_current_domain(),
        "token": EmailVerifyTokenGenerator().token_for_email(booking_account_email),
        "target_view_name": target_view_name,
    }
    body = loader.render_to_string("cciw/bookings/verification_email.txt", c)
    subject = "[CCIW] Booking account"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [booking_account_email])


def send_unrecognised_payment_email(ipn_obj, reason=None):
    c = {
        "domain": common.get_current_domain(),
        "ipn_obj": ipn_obj,
        "reason": reason,
    }

    body = loader.render_to_string("cciw/bookings/unrecognised_payment_email.txt", c)
    subject = "[CCIW] Booking - unrecognised payment"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, settings.WEBMASTER_EMAILS)


def send_pending_payment_email(account, ipn_obj):
    c = {
        "account": account,
        "ipn_obj": ipn_obj,
    }
    body = loader.render_to_string("cciw/bookings/pending_payment_email.txt", c)
    subject = "[CCIW] Booking - pending payment"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])


def send_places_confirmed_email(bookings):
    if not bookings:
        return
    account = bookings[0].account
    if not account.email:
        return

    # We can't use 'processed' here, because this email can be sent
    # in the middle of processing before that flag is updated.
    payment_received_recently = account.payments.received_since(timezone.now() - timedelta(hours=1)).exists()
    c = {
        "domain": common.get_current_domain(),
        "account": account,
        "bookings": bookings,
        "payment_received_recently": payment_received_recently,
        "early_bird_discount_missed": sum(b.early_bird_discount_missed() for b in bookings),
    }
    body = loader.render_to_string("cciw/bookings/place_confirmed_email.txt", c)
    subject = "[CCIW] Booking - place confirmed"

    # Use queued_mail, which uses DB storage, because this function gets
    # triggered from within payment processing, and we want to ensure that
    # network errors won't affect this processing.
    queued_mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    # Email leaders. Bookings could be for different camps, so send different
    # emails.

    # We don't care about timezones, or about accuracy better than 1 day,
    # so use naive UTC datetimes, not aware datetimes.
    today = datetime.utcnow().date()

    for booking in bookings:
        if (booking.camp.start_date - today) < settings.LATE_BOOKING_THRESHOLD:
            c = {
                "domain": common.get_current_domain(),
                "account": account,
                "booking": booking,
                "camp": booking.camp,
            }
            body = loader.render_to_string("cciw/bookings/late_place_confirmed_email.txt", c)
            subject = f"[CCIW] Late booking: {booking.name}"

            emails = admin_emails_for_camp(booking.camp)
            if emails:
                queued_mail.send_mail(subject, body, settings.SERVER_EMAIL, emails)


def send_booking_expiry_mail(account, bookings, expired):
    if not account.email:
        return

    c = {
        "domain": common.get_current_domain(),
        "account": account,
        "bookings": bookings,
        "expired": expired,
        "token": EmailVerifyTokenGenerator().token_for_email(account.email),
    }
    body = loader.render_to_string("cciw/bookings/place_expired_mail.txt", c)
    if expired:
        subject = "[CCIW] Booking expired"
    else:
        subject = "[CCIW] Booking expiry warning"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])


def send_booking_approved_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        "domain": common.get_current_domain(),
        "token": EmailVerifyTokenGenerator().token_for_email(account.email),
        "account": account,
        "booking": booking,
    }
    body = loader.render_to_string("cciw/bookings/place_approved_email.txt", c)
    subject = "[CCIW] Booking - approved"
    queued_mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    return True


def send_booking_confirmed_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        "account": account,
        "booking": booking,
    }
    body = loader.render_to_string("cciw/bookings/place_booked_email.txt", c)
    subject = "[CCIW] Booking - confirmed"
    queued_mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    return True


def send_payment_reminder_emails():
    from cciw.bookings.models import BookingAccount

    accounts = BookingAccount.objects.payments_due()

    subject = "[CCIW] Payment due"
    now = timezone.now()
    for account in accounts:
        if (
            account.last_payment_reminder is not None
            and (now - account.last_payment_reminder) < settings.BOOKING_EMAIL_REMINDER_FREQUENCY
        ):
            continue

        if account.email is None:
            continue

        account.last_payment_reminder = now
        account.save()

        c = {
            "domain": common.get_current_domain(),
            "account": account,
            "token": EmailVerifyTokenGenerator().token_for_email(account.email),
        }
        body = loader.render_to_string("cciw/bookings/payments_due_email.txt", c)
        mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])
