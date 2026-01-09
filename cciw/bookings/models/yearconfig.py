from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from django.conf import settings
from django.core.validators import ValidationError
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
    cancellations_full_refund_cutoff_on = models.DateField(
        help_text="The last date people can cancel bookings and still get a full refund",
        null=True,
        default=None,
        blank=True,
    )

    def __str__(self) -> str:
        return f"Config for {self.year}"

    def clean(self):
        super().clean()
        if (
            self.bookings_open_for_booking_on
            and self.bookings_open_for_entry_on
            and (self.bookings_open_for_booking_on < self.bookings_open_for_entry_on)
        ):
            raise ValidationError("Field 'open for booking' must not be before 'open for data entry'")
        if (
            self.bookings_close_for_initial_period_on
            and self.bookings_open_for_booking_on
            and self.bookings_close_for_initial_period_on < self.bookings_open_for_booking_on
        ):
            raise ValidationError("Field 'close initial booking period' must not be before 'open for booking'")
        if (
            self.bookings_initial_notifications_on
            and self.bookings_close_for_initial_period_on
            and self.bookings_initial_notifications_on <= self.bookings_close_for_initial_period_on
        ):
            raise ValidationError(
                "Field 'send initial bookings notifications' must be after 'close initial booking period'"
            )
        if (
            self.payments_due_on
            and self.bookings_initial_notifications_on
            and self.payments_due_on <= self.bookings_initial_notifications_on
        ):
            raise ValidationError("Field 'payments due on' must be after 'send initial bookings notifications'")


def get_year_config(year: int) -> YearConfig | None:
    return YearConfig.objects.filter(year=year).first()


class YearConfigFetcher:
    """
    Utility that looks up YearConfig objects, with caching to reduce queries
    """

    def __init__(self) -> None:
        self._configs: dict[int, YearConfig | None] = {}

    def lookup_year(self, year: int) -> YearConfig | None:
        self._ensure_configs(years=[year])
        return self._configs.get(year, None)

    def _ensure_configs(self, years: list[int]) -> None:
        missing_years = set(years) - set(self._configs.keys())
        if missing_years:
            configs: list[YearConfig] = list(YearConfig.objects.filter(year__in=missing_years))
            # Ensure we add cache entries for both missing and found
            missing = {year: None for year in years}
            found = {cf.year: cf for cf in configs}
            combined = missing | found
            self._configs.update(combined)


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
    initial_notifications_on: date | None
    payments_due_on: date | None
    cancellations_full_refund_cutoff_on: date | None

    @property
    def closes_for_initial_period_special_needs_on(self) -> date | None:
        if self.closes_for_initial_period_on is None:
            return None
        return self.closes_for_initial_period_on - settings.BOOKINGS_TIME_FOR_SPECIAL_NEEDS_APPROVAL

    @classmethod
    def from_year_config(cls, config: YearConfig, *, prices_are_set: bool) -> BookingOpenData:
        now = timezone.now()
        today = now.date()

        opens_for_booking_on = config.bookings_open_for_booking_on
        opens_for_entry_on = config.bookings_open_for_entry_on
        closes_for_initial_period_on = config.bookings_close_for_initial_period_on
        initial_notifications_on = config.bookings_initial_notifications_on
        payments_due_on = config.payments_due_on
        cancellations_full_refund_cutoff_on = config.cancellations_full_refund_cutoff_on

        if prices_are_set:
            is_open_for_booking = config.bookings_open_for_booking_on <= today
            is_open_for_entry = config.bookings_open_for_entry_on <= today
        else:
            # if prices aren't set, even collecting data is complicated because
            # the form expects to find prices, so we disallow in this case.
            is_open_for_booking = False
            is_open_for_entry = False

            # We also can't say for sure when booking will open for entry/booking,
            # but we can hope someone fills in the data

        return cls(
            opens_for_booking_on=opens_for_booking_on,
            opens_for_entry_on=opens_for_entry_on,
            closes_for_initial_period_on=closes_for_initial_period_on,
            initial_notifications_on=initial_notifications_on,
            payments_due_on=payments_due_on,
            is_open_for_booking=is_open_for_booking,
            is_open_for_entry=is_open_for_entry,
            cancellations_full_refund_cutoff_on=cancellations_full_refund_cutoff_on,
        )

    @classmethod
    def no_info(cls) -> BookingOpenData:
        return cls(
            opens_for_booking_on=None,
            opens_for_entry_on=None,
            closes_for_initial_period_on=None,
            initial_notifications_on=None,
            payments_due_on=None,
            is_open_for_booking=False,
            is_open_for_entry=False,
            cancellations_full_refund_cutoff_on=None,
        )


def get_booking_open_data(year: int) -> BookingOpenData:
    year_config = get_year_config(year)
    if year_config is None:
        return BookingOpenData.no_info()
    return BookingOpenData.from_year_config(year_config, prices_are_set=are_prices_set_for_year(year))


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
