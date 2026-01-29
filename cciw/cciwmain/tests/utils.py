from __future__ import annotations

from datetime import datetime, time

from django.contrib.sites.models import Site

from cciw.cciwmain import common
from cciw.cciwmain.utils import ensure_timezone_aware


def init_query_caches():
    """
    Initialise any cached values that do DB queries.

    This is useful to improve isolation of tests that check the number of queries used.
    """
    common.get_thisyear()
    Site.objects.get_current()


class FuzzyInt(int):
    def __new__(cls: type[FuzzyInt], lowest: int, highest: int) -> FuzzyInt:
        obj = super().__new__(cls, highest)
        obj.lowest = lowest
        obj.highest = highest
        return obj

    def __eq__(self, other: int) -> bool:
        return other >= self.lowest and other <= self.highest

    def __repr__(self):
        return f"[{self.lowest}, {self.highest}]"


def make_datetime(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime.datetime:
    return ensure_timezone_aware(datetime(year, month, day, hour, minute, second))


def date_to_datetime(date_value: datetime.date) -> datetime.datetime:
    if date_value is None:
        return None
    return ensure_timezone_aware(datetime.combine(date_value, time(0, 0, 0)))
