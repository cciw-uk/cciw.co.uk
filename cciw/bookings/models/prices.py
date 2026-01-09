from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import cached_property

from django.db import models
from django.utils import timezone

from cciw.bookings.models.yearconfig import early_bird_is_available, get_early_bird_cutoff_date


# Price types that can be selected in a booking or appear in Prices table.
class PriceType(models.TextChoices):
    FULL = "full", "Full price"
    SECOND_CHILD = "second_child", "2nd child discount"
    THIRD_CHILD = "third_child", "3rd child discount"
    CUSTOM = "custom_discount", "Custom discount"
    # South Wales transport not used from 2015 onwards, kept for historical data
    SOUTH_WALES_TRANSPORT = "south_wales_transport", "South wales transport surcharge (pre 2015)"
    # Deposit not used from 2025 onwards, kept for historical data.
    DEPOSIT = "deposit", "Deposit"
    EARLY_BIRD_DISCOUNT = "early_bird_discount", "Early bird discount"
    BOOKING_FEE = "booking_fee", "Booking fee"


BOOKING_PLACE_PRICE_TYPES = [PriceType.FULL, PriceType.SECOND_CHILD, PriceType.THIRD_CHILD, PriceType.CUSTOM]

# Price types that are used by Price model
VALUED_PRICE_TYPES: list[PriceType] = [val for val in BOOKING_PLACE_PRICE_TYPES if val != PriceType.CUSTOM] + [
    PriceType.SOUTH_WALES_TRANSPORT,
    PriceType.DEPOSIT,
    PriceType.EARLY_BIRD_DISCOUNT,
    PriceType.BOOKING_FEE,
]


# Prices required to open bookings.
# If changing this, PriceInfo.price_* should be changed to tolerate missing data
REQUIRED_PRICE_TYPES: list[PriceType] = [
    v for v in VALUED_PRICE_TYPES if v not in (PriceType.SOUTH_WALES_TRANSPORT, PriceType.DEPOSIT)
]


class PriceQuerySet(models.QuerySet):
    def required_for_booking(self):
        return self.filter(price_type__in=REQUIRED_PRICE_TYPES)

    def for_year(self, year):
        return self.filter(year=year)


class Price(models.Model):
    year = models.PositiveSmallIntegerField()
    price_type = models.CharField(choices=[(pt, pt.label) for pt in VALUED_PRICE_TYPES])
    price = models.DecimalField(decimal_places=2, max_digits=10)

    objects = models.Manager.from_queryset(PriceQuerySet)()

    class Meta:
        unique_together = [("year", "price_type")]

    def __str__(self):
        return f"{self.get_price_type_display()} {self.year} - {self.price}"


@dataclass(frozen=True)
class PriceInfo:
    year: int
    prices: dict[PriceType, Decimal]

    @classmethod
    def get_for_year(cls, year: int) -> PriceInfo | None:
        prices: list[Price] = list(Price.objects.filter(year=year))

        price_dict: dict[PriceType, Decimal] = {p.price_type: p.price for p in prices}
        if not all(pt in price_dict for pt in REQUIRED_PRICE_TYPES):
            # Act as if prices haven't been set - it's easier
            # than dealing with partial information.
            return None

        return cls(year=year, prices=price_dict)

    @property
    def price_full(self) -> Decimal:
        return self.prices[PriceType.FULL]

    @property
    def price_second_child(self) -> Decimal:
        return self.prices[PriceType.SECOND_CHILD]

    @property
    def price_third_child(self) -> Decimal:
        return self.prices[PriceType.THIRD_CHILD]

    @property
    def price_early_bird_discount(self) -> Decimal:
        return self.prices[PriceType.EARLY_BIRD_DISCOUNT]

    @property
    def price_booking_fee(self) -> Decimal:
        return self.prices[PriceType.BOOKING_FEE]

    @property
    def price_list(self) -> list[tuple[str, Decimal]]:
        return [
            ("Full price", self.price_full),
            ("2nd camper from the same family", self.price_second_child),
            ("Subsequent children from the same family", self.price_third_child),
        ]

    @property
    def price_list_with_discounts(self) -> list[tuple[str, Decimal, Decimal]]:
        early_bird_discount = self.price_early_bird_discount
        return [(caption, p, p - early_bird_discount) for caption, p in self.price_list]

    @cached_property
    def early_bird_is_available(self) -> bool:
        return early_bird_is_available(year=self.year, booked_at=timezone.now())

    @cached_property
    def early_bird_date(self) -> datetime:
        return get_early_bird_cutoff_date(self.year)


def are_prices_set_for_year(year: int) -> bool:
    return PriceInfo.get_for_year(year=year) is not None
