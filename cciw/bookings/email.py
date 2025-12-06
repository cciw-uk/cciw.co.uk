from __future__ import annotations

import base64
import binascii
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import mailer as queued_mail
from django.conf import settings
from django.core import mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template import loader
from django.urls import reverse
from django.utils import timezone

from cciw.cciwmain import common
from cciw.officers.email import admin_emails_for_camp


class VerifyFailed:
    pass


@dataclass
class VerifyExpired:
    email: str


class EmailVerifyTokenGenerator:
    """
    Strategy object used to generate and check tokens for the email verification
    mechanism.
    """

    def __init__(self, key: str | None = None):
        self.signer = TimestampSigner(salt="cciw.bookings.EmailVerifyTokenGenerator", key=key)

    def token_for_email(self, email):
        """
        Returns a verification token for the provided email address
        """
        return self.url_safe_encode(self.signer.sign(email))

    def email_from_token(self, token, max_age=None) -> str | VerifyFailed | VerifyExpired:
        """
        Extracts the verified email address from the token, or a VerifyFailed
        constant if verification failed, or VerifyExpired if the link expired.
        """
        if max_age is None:
            max_age = settings.BOOKING_EMAIL_VERIFY_TIMEOUT
        try:
            unencoded_token = self.url_safe_decode(token)
        except (UnicodeDecodeError, binascii.Error):
            return VerifyFailed()
        try:
            return self.signer.unsign(unencoded_token, max_age=max_age)
        except (SignatureExpired,):
            return VerifyExpired(self.signer.unsign(unencoded_token))
        except (BadSignature,):
            return VerifyFailed()

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


def build_url(*, view_name: str, domain: str | None = None) -> str:
    url = reverse(view_name)
    domain = domain or common.get_current_domain()
    return f"https://{domain}{url}"


def build_url_with_booking_token(
    *,
    view_name: str,
    email: str,
    token_generator: Callable[[], EmailVerifyTokenGenerator] = EmailVerifyTokenGenerator,
    domain: str | None = None,
) -> str:
    url = build_url(view_name=view_name, domain=domain)
    token = token_generator().token_for_email(email)
    return f"{url}?bt={token}"


def send_verify_email(request, booking_account_email, target_view_name=None):
    if target_view_name is None:
        target_view_name = "cciw-bookings-verify_and_continue"
    c = {"verify_url": build_url_with_booking_token(view_name=target_view_name, email=booking_account_email)}
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

    # We can't use 'processed_at' here, because this email can be sent
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


def send_booking_approved_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        "book_and_pay_url": build_url_with_booking_token(
            view_name="cciw-bookings-basket_list_bookings", email=account.email
        ),
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
            account.last_payment_reminder_at is not None
            and (now - account.last_payment_reminder_at) < settings.BOOKING_EMAIL_REMINDER_FREQUENCY
        ):
            continue

        if account.email is None:
            continue

        account.last_payment_reminder_at = now
        account.save()

        c = {
            "pay_url": build_url_with_booking_token(view_name="cciw-bookings-pay", email=account.email),
            "start_url": build_url(view_name="cciw-bookings-start"),
            "account": account,
        }
        body = loader.render_to_string("cciw/bookings/payments_due_email.txt", c)
        mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])
