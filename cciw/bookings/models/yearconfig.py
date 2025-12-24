from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

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
    bookings_open_for_booking_on = models.DateField(
        verbose_name="open for booking", help_text="The date that we allow people to press 'Book'"
    )
    bookings_close_for_initial_period_on = models.DateField(
        verbose_name="close initial booking period",
        help_text="The last date of the initial booking period. Bookings made on and before this date are considered together.",
    )
    bookings_initial_notifications_on = models.DateField(
        verbose_name="send initial bookings notifications",
        help_text="The date we will have sent initial notifications about bookings, after the initial booking period",
    )
    payments_due_on = models.DateField(
        help_text="The date we expect payment for places to be made (unless a payment plan is agreed on)"
    )

    def __str__(self) -> str:
        return f"Config for {self.year}"


def get_year_config(year: int) -> YearConfig | None:
    return YearConfig.objects.filter(year=year).first()


def any_bookings_possible(year: int) -> bool:
    camps: Iterable[Camp] = Camp.objects.filter(year=year)
    return any(c.get_places_left().total > 0 and c.is_open_for_bookings for c in camps)


@dataclass(frozen=True)
class BookingOpenData:
    is_open_for_booking: bool
    is_open_for_entry: bool

    opens_for_booking_on: date | None
    opens_for_entry_on: date | None
    closes_for_initial_period_on: date | None

    @classmethod
    def from_year_config(cls, config: YearConfig) -> BookingOpenData:
        now = timezone.now()
        today = now.date()
        return cls(
            opens_for_booking_on=config.bookings_open_for_booking_on,
            opens_for_entry_on=config.bookings_open_for_entry_on,
            closes_for_initial_period_on=config.bookings_close_for_initial_period_on,
            is_open_for_booking=config.bookings_open_for_booking_on <= today,
            is_open_for_entry=config.bookings_open_for_entry_on <= today,
        )

    @classmethod
    def no_info(cls) -> BookingOpenData:
        return cls(
            opens_for_booking_on=None,
            opens_for_entry_on=None,
            closes_for_initial_period_on=None,
            is_open_for_booking=False,
            is_open_for_entry=False,
        )


def get_booking_open_data(year: int) -> BookingOpenData:
    if not are_prices_set_for_year(year):
        # even collecting data is complicated if prices aren't set,
        # because the form expects to find prices, so we disallow
        # in this case, and we can't say when it will open because
        # we don't know when prices which actually be entered.
        return BookingOpenData.no_info()

    year_config = get_year_config(year)
    if year_config is None:
        return BookingOpenData.no_info()
    return BookingOpenData.from_year_config(year_config)


def get_booking_open_data_thisyear() -> BookingOpenData:
    return get_booking_open_data(common.get_thisyear())


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
