"""
Models relating to the queue system
"""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from cciw.bookings.models.yearconfig import YearConfig, get_year_config
from cciw.cciwmain.models import Camp

if TYPE_CHECKING:
    from .bookings import Booking

# TODO - do we need this, or should it be a 'active' boolean to indicate `withdrawn',
# with the other two states determined by `Booking.state`?


class QueueState(models.TextChoices):
    # Initial state:
    WAITING = "waiting", "Waiting"

    # The place is accepted and booked:
    ACCEPTED = "accepted", "Accepted"

    # Booker no longer wants the place:
    WITHDRAWN = "withdrawn", "Withdrawn"


class BookingQueueEntryQuerySet(models.QuerySet):
    pass


class BookingQueueEntryManagerBase(models.Manager):
    def create_for_booking(self, booking: Booking):
        return self.create(booking=booking, state=QueueState.WAITING)


BookingQueueEntryManager = BookingQueueEntryManagerBase.from_queryset(BookingQueueEntryQuerySet)


class BookingQueueEntry(models.Model):
    booking = models.OneToOneField(to="bookings.Booking", on_delete=models.CASCADE, related_name="queue_entry")
    state = models.CharField(choices=QueueState, default=QueueState.WAITING)

    # Fields relating to priority rules:
    created_at = models.DateTimeField(default=timezone.now)
    officer_child = models.BooleanField(default=False)

    @cached_property
    def tiebreaker(self) -> str:
        # A "random" number used to implement our "lottery" system.
        # We actually use a pseudorandom number by hashing some internal
        # fields that can't be gamed easily.
        internal_state = self.created_at.timestamp() * self.id
        hashed = hashlib.sha256(data=bytes(str(internal_state), "utf-8"))
        return hashed.hexdigest()

    @cached_property
    def tiebreaker_display(self) -> int:
        # We make it user presentable by turning it into a number
        # between 0 and 65000 ish
        return int(self.tiebreaker[0:4], 16)

    objects = BookingQueueEntryManager()

    class Meta:
        verbose_name = "queue entry"
        verbose_name_plural = "queue entries"

    def __str__(self):
        return f"Queue entry for {self.booking.name}"

    @property
    def is_current(self) -> bool:
        return self.state != QueueState.WITHDRAWN

    def make_current(self) -> None:
        if self.state == QueueState.WITHDRAWN:
            self.state = QueueState.WAITING
            self.save()


@dataclass
class RankInfo:
    queue_position_rank: int
    previous_attendance_score: int


def rank_queue_bookings(camp: Camp) -> list[Booking]:
    from cciw.bookings.models import Booking

    queue_bookings = list(
        Booking.objects.for_camp(camp)
        .waiting_in_queue()
        .select_related(
            "camp",
            "queue_entry",
        )
    )
    if not queue_bookings:
        return []

    # Some of these things could be done using SQL window functions, but some
    # are much easier with Python.

    # So we prefer Python when it makes sense.

    year_config = get_year_config(camp.year)
    assert year_config is not None
    add_rank_info(queue_bookings, year_config)

    def is_officer_child_key(booking: Booking) -> int:
        return 0 if booking.queue_entry.officer_child else 1

    def queue_position_key(booking: Booking) -> int:
        return booking.rank_info.queue_position_rank

    def previous_attendance_key(booking: Booking) -> int:
        # More attendance is better.
        return -booking.rank_info.previous_attendance_score

    def tiebreaker_key(booking: Booking) -> int:
        return booking.queue_entry.tiebreaker

    def overall_key(booking: Booking) -> tuple:
        return (
            is_officer_child_key(booking),
            queue_position_key(booking),
            previous_attendance_key(booking),
            tiebreaker_key(booking),
        )

    queue_bookings.sort(key=overall_key)
    return list(queue_bookings)


type BookingId = int


def add_rank_info(bookings: list[Booking], year_config: YearConfig):
    queue_position_ranks: dict[BookingId, int] = get_queue_position_ranks(bookings, year_config)
    attendance_scores: dict[BookingId, int] = get_previous_attendance_score(bookings, year_config)
    for booking in bookings:
        booking.rank_info = RankInfo(
            queue_position_rank=queue_position_ranks[booking.id],
            previous_attendance_score=attendance_scores[booking.id],
        )


def get_queue_position_ranks(bookings: list[Booking], year_config: YearConfig):
    """
    Define 'queue_position_ranks', based on 'queue_position' and the initial booking period.
    """

    # Everyone booked within the initial period is first equal,
    # everyone later is in ascending order.

    def is_in_initial_period(booking: Booking) -> bool:
        return booking.queue_entry.created_at.date() <= year_config.bookings_close_for_initial_period_on

    def initial_sort_key(booking: Booking) -> tuple:
        # Those in initial period should come first
        return (not is_in_initial_period(booking), booking.queue_entry.created_at)

    # Sort so that those in the initial period are first,
    # the rest are in order of their `created_at`
    sorted_bookings = sorted(bookings, key=initial_sort_key)
    counter = itertools.count(start=2)
    ranks = {b.id: (1 if is_in_initial_period(b) else next(counter)) for b in sorted_bookings}
    return ranks


def get_previous_attendance_score(bookings: list[Booking], year_config: YearConfig) -> dict[BookingId, int]:
    from cciw.bookings.models import Booking

    camper_ids: list[str] = [b.fuzzy_camper_id for b in bookings]
    attendance_counts: dict[str, str | int] = (
        Booking.objects.booked()
        .filter(camp__year__lt=year_config.year, fuzzy_camper_id__in=camper_ids)
        .values("fuzzy_camper_id")
        .annotate(attendance_count=models.Count("id"))
    )
    counts_by_fuzzy_camper_id: dict[str, int] = {d["fuzzy_camper_id"]: d["attendance_count"] for d in attendance_counts}
    counts_by_id: dict[BookingId, int] = {b.id: counts_by_fuzzy_camper_id.get(b.fuzzy_camper_id, 0) for b in bookings}
    return counts_by_id
