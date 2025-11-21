from collections import defaultdict
from decimal import Decimal

from django.db import models


# Price types that can be selected in a booking or appear in Prices table.
class PriceType(models.IntegerChoices):
    FULL = 0, "Full price"
    SECOND_CHILD = 1, "2nd child discount"
    THIRD_CHILD = 2, "3rd child discount"
    CUSTOM = 3, "Custom discount"
    # South Wales transport not used from 2015 onwards, kept for historical data
    SOUTH_WALES_TRANSPORT = 4, "South wales transport surcharge (pre 2015)"
    # Deposit not used from 2025 onwards, kept for historical data.
    DEPOSIT = 5, "Deposit"
    EARLY_BIRD_DISCOUNT = 6, "Early bird discount"


BOOKING_PLACE_PRICE_TYPES = [PriceType.FULL, PriceType.SECOND_CHILD, PriceType.THIRD_CHILD, PriceType.CUSTOM]

# Price types that are used by Price model
VALUED_PRICE_TYPES = [val for val in BOOKING_PLACE_PRICE_TYPES if val != PriceType.CUSTOM] + [
    PriceType.SOUTH_WALES_TRANSPORT,
    PriceType.DEPOSIT,
    PriceType.EARLY_BIRD_DISCOUNT,
]


# Prices required to open bookings.
REQUIRED_PRICE_TYPES = [v for v in VALUED_PRICE_TYPES if v not in (PriceType.SOUTH_WALES_TRANSPORT, PriceType.DEPOSIT)]


class PriceQuerySet(models.QuerySet):
    def required_for_booking(self):
        return self.filter(price_type__in=REQUIRED_PRICE_TYPES)

    def for_year(self, year):
        return self.filter(year=year)


class Price(models.Model):
    year = models.PositiveSmallIntegerField()
    price_type = models.PositiveSmallIntegerField(choices=[(pt, pt.label) for pt in VALUED_PRICE_TYPES])
    price = models.DecimalField(decimal_places=2, max_digits=10)

    objects = models.Manager.from_queryset(PriceQuerySet)()

    class Meta:
        unique_together = [("year", "price_type")]

    def __str__(self):
        return f"{self.get_price_type_display()} {self.year} - {self.price}"


class PriceChecker:
    """
    Utility that looks up prices, with caching to reduce queries
    """

    # We don't look up prices immediately, but lazily, because there are
    # quite a few paths that don't need the price at all,
    # and they can happen in a loop e.g. BookingAccount.get_balance_full()

    def __init__(self, expected_years: list[int] | None = None):
        self._prices = defaultdict(dict)
        self._expected_years = expected_years or []

    def _fetch_prices(self, year: int):
        if year in self._prices:
            return
        # Try to get everything we think we'll need in a single query,
        # and cache for later.
        years = set(self._expected_years + [year])
        for price in Price.objects.filter(year__in=years):
            self._prices[price.year][price.price_type] = price.price

    def get_price(self, year: int, price_type: PriceType) -> Decimal:
        self._fetch_prices(year)
        return self._prices[year][price_type]

    def get_full_price(self, year: int) -> Decimal:
        return self.get_price(year, PriceType.FULL)

    def get_second_child_price(self, year: int) -> Decimal:
        return self.get_price(year, PriceType.SECOND_CHILD)

    def get_third_child_price(self, year: int) -> Decimal:
        return self.get_price(year, PriceType.THIRD_CHILD)

    def get_early_bird_discount(self, year: int) -> Decimal:
        return self.get_price(year, PriceType.EARLY_BIRD_DISCOUNT)


def are_prices_set_for_year(year: int) -> bool:
    return Price.objects.required_for_booking().filter(year=year).count() == len(REQUIRED_PRICE_TYPES)
