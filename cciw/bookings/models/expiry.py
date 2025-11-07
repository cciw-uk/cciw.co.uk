from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from ..email import send_booking_expiry_mail
from .bookings import Booking


def expire_bookings(now: datetime | None = None):
    if now is None:
        now = timezone.now()

    # For the warning, we send out between 12 and 13 hours before booking
    # expires.  This relies on this job being run once an hour, and only
    # once an hour.
    nowplus12h = now + timedelta(0, 3600 * 12)
    nowplus13h = now + timedelta(0, 3600 * 13)

    unconfirmed = Booking.objects.unconfirmed().order_by("account")
    to_warn = unconfirmed.filter(booking_expires_at__lte=nowplus13h, booking_expires_at__gte=nowplus12h)
    to_expire = unconfirmed.filter(booking_expires_at__lte=now)

    for booking_set, expired in [(to_expire, True), (to_warn, False)]:
        groups = []
        last_account_id = None
        for b in booking_set:
            if last_account_id is None or b.account_id != last_account_id:
                group = []
                groups.append(group)
            group.append(b)
            last_account_id = b.account_id

        for group in groups:
            account = group[0].account
            if account.get_pending_payment_total(now=now) > Decimal("0.00"):
                continue

            if expired:
                for b in group:
                    b.expire()
            send_booking_expiry_mail(account, group, expired)
