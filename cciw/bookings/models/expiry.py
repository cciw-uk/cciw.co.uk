from collections.abc import Sequence

from django.utils import timezone

from ..email import send_booking_expired_mail
from .bookings import Booking


def expire_bookings():
    now = timezone.now()

    will_expire: Sequence[Booking] = Booking.objects.booked().expiry_due(now=now)

    for booking in will_expire:
        booking.expire_expiring_place()
        send_booking_expired_mail(booking)
