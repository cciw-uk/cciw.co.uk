# TODO We may want to move these utilities into a `dates` module. We probably
# want a `BookingConfig` model that gives dates for booking opening, and these
# may become method on that.
from datetime import datetime

from django.utils import timezone

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp


def any_bookings_possible(year: int):
    camps = Camp.objects.filter(year=year)
    return any(c.get_places_left().total > 0 and c.is_open_for_bookings for c in camps)


def is_booking_open(year: int):
    """
    When passed a given year, returns True if booking is open.
    """
    from .prices import REQUIRED_PRICE_TYPES, Price

    return (
        Price.objects.required_for_booking().filter(year=year).count() == len(REQUIRED_PRICE_TYPES)
    ) and Camp.objects.filter(year=year).exists()


def is_booking_open_thisyear():
    return is_booking_open(common.get_thisyear())


def most_recent_booking_year():
    from .bookings import Booking

    booking = Booking.objects.booked().order_by("-camp__year").select_related("camp").first()
    if booking:
        return booking.camp.year
    else:
        return None


def get_early_bird_cutoff_date(year: int) -> datetime:
    # 1st May
    return datetime(year, 5, 1, tzinfo=timezone.get_default_timezone())


def early_bird_is_available(year: int, booked_at_date: datetime):
    return booked_at_date < get_early_bird_cutoff_date(year)
