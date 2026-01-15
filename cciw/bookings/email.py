from __future__ import annotations

import base64
import binascii
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from django.conf import settings
from django.core import mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from paypal.standard.ipn.models import PayPalIPN

from cciw.bookings.models.queue import BookingQueueEntry
from cciw.cciwmain import common
from cciw.utils.functional import partition

from .models.accounts import BookingAccount
from .models.bookings import Booking


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


def build_url(*, view_name: str, view_kwargs: dict | None = None, domain: str | None = None) -> str:
    url = reverse(view_name, kwargs=view_kwargs)
    domain = domain or common.get_current_domain()
    return f"https://{domain}{url}"


def build_url_with_booking_token(
    *,
    view_name: str,
    email: str,
    token_generator: Callable[[], EmailVerifyTokenGenerator] = EmailVerifyTokenGenerator,
    domain: str | None = None,
    view_kwargs: dict | None = None,
) -> str:
    url = build_url(view_name=view_name, view_kwargs=view_kwargs, domain=domain)
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


def send_pending_payment_email(account: BookingAccount, ipn_obj: PayPalIPN):
    c = {
        "account": account,
        "ipn_obj": ipn_obj,
    }
    body = loader.render_to_string("cciw/bookings/pending_payment_email.txt", c)
    subject = "[CCIW] Pending payment"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])


def send_payment_received_email(account: BookingAccount, ipn_obj: PayPalIPN):
    c = {
        "account": account,
        "ipn_obj": ipn_obj,
    }
    body = loader.render_to_string("cciw/bookings/payment_received_email.txt", c)
    subject = "[CCIW] Payment received"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])


def send_places_allocated_emails(account: BookingAccount, bookings: Sequence[Booking]) -> None:
    assert bookings
    assert all(booking.account == account for booking in bookings)
    if not account.email:
        return

    expiring_bookings, non_expiring_bookings = partition(bookings, lambda b: b.will_expire)

    for booking in expiring_bookings:
        # Send individual emails, because there are actions are we don't
        # want to confuse things.
        c = {
            "domain": common.get_current_domain(),
            "account": account,
            "booking": booking,
            "booking_expires_after_display": settings.BOOKING_EXPIRES_FOR_UNCONFIRMED_BOOKING_AFTER_DISPLAY,
            "accept_place_url": make_accept_place_url(booking),
            "cancel_place_url": make_cancel_place_url(booking),
        }
        body = loader.render_to_string("cciw/bookings/expiring_place_allocated_email.txt", c)
        subject = f"[CCIW] Booking - place allocated for {booking.name}"
        mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    if non_expiring_bookings:
        # We can send these all together, there are no actions to take.
        c = {
            "domain": common.get_current_domain(),
            "account": account,
            "bookings": bookings,
        }
        body = loader.render_to_string("cciw/bookings/places_confirmed_email.txt", c)
        subject = "[CCIW] Booking - places confirmed"
        mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    BookingQueueEntry.objects.filter(id__in=[b.queue_entry.id for b in bookings]).update(
        accepted_notification_sent_at=timezone.now()
    )


def make_accept_place_url(booking: Booking) -> str:
    return build_url_with_booking_token(
        view_name="cciw-bookings-accept_place", email=booking.account.email, view_kwargs={"booking_id": booking.id}
    )


def make_cancel_place_url(booking: Booking) -> str:
    return build_url_with_booking_token(
        view_name="cciw-bookings-cancel_place", email=booking.account.email, view_kwargs={"booking_id": booking.id}
    )


def send_places_declined_email(account: BookingAccount, bookings: Sequence[Booking]) -> None:
    assert bookings
    assert all(booking.account == account for booking in bookings)
    if not account.email:
        return

    c = {
        "domain": common.get_current_domain(),
        "account": account,
        "bookings": bookings,
        "account_overview_url": build_url_with_booking_token(
            view_name="cciw-bookings-account_overview", email=account.email
        ),
    }
    body = loader.render_to_string("cciw/bookings/places_declined_email.txt", c)
    subject = "[CCIW] Booking - places declined"

    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])
    BookingQueueEntry.objects.filter(id__in=[b.queue_entry.id for b in bookings]).update(
        declined_notification_sent_at=timezone.now()
    )


def send_booking_approved_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        "book_url": build_url_with_booking_token(view_name="cciw-bookings-basket_list_bookings", email=account.email),
        "account": account,
        "booking": booking,
    }
    body = loader.render_to_string("cciw/bookings/place_approved_email.txt", c)
    subject = "[CCIW] Booking - approved"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    return True


def send_booking_confirmed_mail(booking: Booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        "account": account,
        "booking": booking,
    }
    body = loader.render_to_string("cciw/bookings/place_booked_email.txt", c)
    subject = "[CCIW] Booking - confirmed"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])

    return True


def send_booking_expired_mail(booking: Booking):
    account = booking.account
    c = {
        "account": account,
        "booking": booking,
    }
    body = loader.render_to_string("cciw/bookings/place_expired_email.txt", c)
    subject = "[CCIW] Booking expired"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, [account.email])


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
