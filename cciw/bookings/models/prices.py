from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import models


# Price types that can be selected in a booking or appear in Prices table.
class PriceType(models.TextChoices):
    FULL = "full", "Full price"
    SECOND_CHILD = "second_child", "2nd child discount"
    THIRD_CHILD = "third_child", "3rd child discount"
    CUSTOM = "custom_discount", "Custom discount"
    # Deposit not used from 2025 onwards, kept for historical data.
    DEPOSIT = "deposit", "Deposit"
    BOOKING_FEE = "booking_fee", "Booking fee"


# We have some old values that are no longer in the enum,
# but are in the historical data in the `Price` table.
# - South Wales transport fee: not used from 2015 onwards, kept for historical data
#   "south_wales_transport"
# - Discount for people booking early in the year
#   "early_bird_discount"


BOOKING_PLACE_PRICE_TYPES = [PriceType.FULL, PriceType.SECOND_CHILD, PriceType.THIRD_CHILD, PriceType.CUSTOM]

# Price types that are used by Price model
VALUED_PRICE_TYPES: list[PriceType] = [val for val in BOOKING_PLACE_PRICE_TYPES if val != PriceType.CUSTOM] + [
    PriceType.DEPOSIT,
    PriceType.BOOKING_FEE,
]


# Prices required to open bookings.
# If changing this, PriceInfo.price_* should be changed to tolerate missing data
REQUIRED_PRICE_TYPES: list[PriceType] = [v for v in VALUED_PRICE_TYPES if v not in (PriceType.DEPOSIT,)]


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
    def price_booking_fee(self) -> Decimal:
        return self.prices[PriceType.BOOKING_FEE]

    @property
    def price_list(self) -> list[tuple[str, Decimal]]:
        return [
            ("Full price", self.price_full),
            ("2nd camper from the same family", self.price_second_child),
            ("Subsequent children from the same family", self.price_third_child),
        ]


def are_prices_set_for_year(year: int) -> bool:
    return PriceInfo.get_for_year(year=year) is not None
