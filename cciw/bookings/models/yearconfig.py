from collections.abc import Iterable
from datetime import datetime

from django.db import models
from django.utils import timezone

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp

from .prices import are_prices_set_for_year


class YearConfig(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    bookings_open_for_entry_on = models.DateField(
        verbose_name="open for data entry", help_text="The date that people can start to fill in booking details"
    )
    bookings_open_for_booking_at = models.DateTimeField(
        verbose_name="open for booking", help_text="The date that we allow people to press 'Book'"
    )

    def __str__(self) -> str:
        return f"Config for {self.year}"


def get_year_config(year: int) -> YearConfig | None:
    return YearConfig.objects.filter(year=year).first()


def any_bookings_possible(year: int) -> bool:
    camps: Iterable[Camp] = Camp.objects.filter(year=year)
    return any(c.get_places_left().total > 0 and c.is_open_for_bookings for c in camps)


def is_booking_open(year: int) -> bool:
    """
    When passed a given year, returns True if booking is open.
    """
    if not are_prices_set_for_year(year):
        return False

    year_config = get_year_config(year)
    if year_config is None:
        return False

    if timezone.now() < year_config.bookings_open_for_booking_at:
        return False

    return True


def is_booking_open_thisyear() -> bool:
    return is_booking_open(common.get_thisyear())


def most_recent_booking_year() -> int | None:
    from .bookings import Booking

    booking = Booking.objects.booked().order_by("-camp__year").select_related("camp").first()
    if booking:
        return booking.camp.year
    else:
        return None


def get_early_bird_cutoff_date(year: int) -> datetime:
    # 1st May
    return datetime(year, 5, 1, tzinfo=timezone.get_default_timezone())


def early_bird_is_available(year: int, booked_at_date: datetime) -> bool:
    return booked_at_date < get_early_bird_cutoff_date(year)
