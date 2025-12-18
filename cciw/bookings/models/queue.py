"""
Models relating to the queue system
"""

from __future__ import annotations

import hashlib
import itertools
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Literal

from django.db import models
from django.db.models import Value, functions
from django.db.models.enums import TextChoices
from django.utils import timezone

from cciw.accounts.models import User
from cciw.bookings.models.constants import Sex
from cciw.bookings.models.yearconfig import YearConfig, get_year_config
from cciw.cciwmain.models import Camp, PlacesLeft

if TYPE_CHECKING:
    from .bookings import Booking


# TODO - use this value as a validation issue.
FIRST_TIMER_PERCENTAGE = 10


class BookingQueueEntryQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(is_active=False)

    def not_in_use(self, now: datetime):
        # See also BookingQuerySet.not_in_use()
        return self.filter(booking__camp__end_date__lt=now.date())

    def older_than(self, before_datetime: datetime):
        # See also BookingQuerySet.older_than()
        return self.filter(created_at__lt=before_datetime, booking__camp__end_date__lt=before_datetime)


class BookingQueueEntryManagerBase(models.Manager):
    def create_for_booking(self, booking: Booking):
        return self.create(
            booking=booking,
            is_active=True,
            sibling_surname=booking.last_name,
            sibling_booking_account=booking.account,
        )


BookingQueueEntryManager = BookingQueueEntryManagerBase.from_queryset(BookingQueueEntryQuerySet)


class BookingQueueEntry(models.Model):
    booking = models.OneToOneField(to="bookings.Booking", on_delete=models.CASCADE, related_name="queue_entry")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Fields relating to priority rules:
    enqueued_at = models.DateTimeField(default=timezone.now)
    officer_child = models.BooleanField(default=False)
    first_timer_allocated = models.BooleanField(default=False)

    # Siblings are decided using the booking account and a surname.
    # These default to the values on the Booking model, but we make them editable
    # to allow for corrections in cases where this is wrong.
    sibling_booking_account = models.ForeignKey("bookings.BookingAccount", on_delete=models.PROTECT)
    sibling_surname = models.CharField()
    sibling_fuzzy_id = models.GeneratedField(
        expression=functions.Concat(
            functions.Lower("sibling_surname"),
            Value("-"),
            functions.Cast("sibling_booking_account_id", output_field=models.CharField()),
        ),
        output_field=models.CharField(),
        db_persist=True,
    )

    # Internal only:
    erased_at = models.DateTimeField(null=True, blank=True, default=None)

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

    def get_current_field_data(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    def save_fields_changed_action_log(self, *, user: User, old_fields: dict) -> QueueEntryActionLog:
        new_fields = self.get_current_field_data()
        changed: list[dict] = []
        for key, value in new_fields.items():
            old_value = old_fields[key]
            if old_value != value:
                changed.append({"name": key, "old_value": old_value, "new_value": value})
        details = {"fields_changed": changed}
        return self.action_logs.create(user=user, action_type=QueueEntryActionLogType.FIELDS_CHANGED, details=details)

    objects = BookingQueueEntryManager()

    class Meta:
        verbose_name = "queue entry"
        verbose_name_plural = "queue entries"

    def __str__(self):
        return f"Queue entry for {self.booking.name}"

    def make_active(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.save()


class QueueCutoff(StrEnum):
    UNDECIDED = "U"
    ACCEPTED = "A"
    AFTER_TOTAL_CUTOFF = "T"
    AFTER_MALE_CUTOFF = "M"
    AFTER_FEMALE_CUTOFF = "F"


@dataclass
class RankInfo:
    queue_position_rank: int
    previous_attendance_score: int
    in_previous_year_waiting_list: bool
    sibling_bonus: int
    cutoff_state: QueueCutoff = QueueCutoff.UNDECIDED


class QueueEntryActionLogType(TextChoices):
    FIELDS_CHANGED = "fields_changed", "fields changed"


class QueueEntryActionLog(models.Model):
    queue_entry = models.ForeignKey(BookingQueueEntry, related_name="action_logs", on_delete=models.CASCADE)
    action_type = models.CharField(choices=QueueEntryActionLogType)
    created_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="queue_entry_actions_performed")
    details = models.JSONField(default=dict, blank=True)


def rank_queue_bookings(*, camp: Camp, year_config: YearConfig) -> list[Booking]:
    from cciw.bookings.models import Booking

    assert camp.year == year_config.year

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
    add_rank_info(queue_bookings, year_config, camp)

    def is_officer_child_key(booking: Booking) -> int:
        return 0 if booking.queue_entry.officer_child else 1

    def queue_position_key(booking: Booking) -> int:
        return booking.rank_info.queue_position_rank

    def previous_attendance_key(booking: Booking) -> int:
        # More attendance is better.
        return -booking.rank_info.previous_attendance_score

    def first_timer_key(booking: Booking) -> int:
        return 0 if booking.queue_entry.first_timer_allocated else 1

    def previous_year_waiting_list_key(booking: Booking) -> int:
        # In the list means higher priority
        return 0 if booking.rank_info.in_previous_year_waiting_list else 1

    def sibling_bonus_key(booking: Booking) -> int:
        # More siblings is better
        return -booking.rank_info.sibling_bonus

    def tiebreaker_key(booking: Booking) -> int:
        return booking.queue_entry.tiebreaker

    def overall_key(booking: Booking) -> tuple:
        return (
            is_officer_child_key(booking),
            queue_position_key(booking),
            previous_attendance_key(booking),
            first_timer_key(booking),
            previous_year_waiting_list_key(booking),
            sibling_bonus_key(booking),
            tiebreaker_key(booking),
        )

    queue_bookings.sort(key=overall_key)
    return list(queue_bookings)


type BookingId = int


def add_rank_info(bookings: list[Booking], year_config: YearConfig, camp: Camp):
    queue_position_ranks: dict[BookingId, int] = get_queue_position_ranks(bookings, year_config)
    attendance_counts: dict[BookingId, int] = get_previous_attendance_counts(bookings, year_config)
    in_previous_year_waiting_list_info: dict[BookingId, bool] = get_previous_waiting_list_status(bookings, year_config)
    sibling_bonus_scores: dict[BookingId, int] = get_sibling_bonus_scores(
        bookings,
        camp,
        attendance_counts=attendance_counts,
        in_previous_year_waiting_list_info=in_previous_year_waiting_list_info,
    )
    for booking in bookings:
        booking.rank_info = RankInfo(
            queue_position_rank=queue_position_ranks[booking.id],
            # score is currently the same as the count - the more attendance,
            # the better.
            previous_attendance_score=attendance_counts[booking.id],
            in_previous_year_waiting_list=in_previous_year_waiting_list_info[booking.id],
            sibling_bonus=sibling_bonus_scores[booking.id],
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


def get_previous_attendance_counts(bookings: list[Booking], year_config: YearConfig) -> dict[BookingId, int]:
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


def get_previous_attendance_count(booking: Booking) -> int:
    year_config = get_year_config(booking.camp.year)
    counts = get_previous_attendance_counts([booking], year_config)
    return counts[booking.id]


def get_previous_waiting_list_status(bookings: list[Booking], year_config: YearConfig) -> dict[BookingId, bool]:
    """
    Get info about whether bookings were in waiting list (and not offered a place) in the previous year
    """
    # 2026 only: we didn't have a real "waiting list" record in 2025, so for
    # this year, we will assume that anyone who filled in details but didn't get
    # a place was on the "waiting list".

    # For 2027 and later we should change this to be based on BookingQueueEntry
    from cciw.bookings.models import Booking

    camper_ids: list[str] = [b.fuzzy_camper_id for b in bookings]
    previous_year = year_config.year - 1
    previous_year_waiting_list = (
        Booking.objects.in_basket()
        .filter(camp__year=previous_year, fuzzy_camper_id__in=camper_ids)
        .values("fuzzy_camper_id")
        .annotate(queue_count=models.Count("id"))
    )
    in_waiting_list_by_fuzzy_camper_id: dict[str, int] = {
        d["fuzzy_camper_id"]: d["queue_count"] for d in previous_year_waiting_list
    }
    in_waiting_list_by_id: dict[BookingId, bool] = {
        b.id: in_waiting_list_by_fuzzy_camper_id.get(b.fuzzy_camper_id, 0) > 0 for b in bookings
    }
    return in_waiting_list_by_id


def get_sibling_bonus_scores(
    bookings: list[Booking],
    camp: Camp,
    *,
    attendance_counts: dict[BookingId, int],
    in_previous_year_waiting_list_info: dict[BookingId, bool],
) -> dict[BookingId, int]:
    from cciw.bookings.models import Booking

    siblings_dict = find_siblings(bookings, camp)

    # We are supposed to give a score for siblings "already attending". However,
    # we don't know who is actually attending yet (we are trying to decide that,
    # a circular dependency).

    # So, we instead give points for any sibling with a high probability of being
    # on the camp.

    # Some may already be booked, in which case the probability is 1.
    # (though, at the point this is used and relevant, this is probably going to be zero)
    already_booked_ids: set[BookingId] = set(Booking.objects.for_camp(camp).booked().values_list("id", flat=True))

    # For the rest, we can use information we already have to guess if they have
    # a high probability of being accepted.

    # These are based on the ranking criteria, but simplified a bit.
    is_officer_child_ids: set[BookingId] = set(b.id for b in bookings if b.queue_entry.officer_child)
    has_attended_before_ids: set[BookingId] = set(b_id for b_id, count in attendance_counts.items() if count > 0)
    is_first_timer_ids: set[BookingId] = set(b.id for b in bookings if b.queue_entry.first_timer_allocated)
    in_previous_year_waiting_list_ids: set[BookingId] = set(
        b_id for b_id, in_list in in_previous_year_waiting_list_info.items() if in_list
    )

    high_probability_booking_ids = (
        already_booked_ids
        # Anyone hitting one of the top 4 criteria has a high chance of getting a place
        | is_officer_child_ids
        | has_attended_before_ids
        | is_first_timer_ids
        | in_previous_year_waiting_list_ids
    )

    retval: dict[BookingId, int] = {}
    for booking in bookings:
        booking_siblings = siblings_dict[booking.id]
        siblings_with_high_probability = high_probability_booking_ids & booking_siblings
        # The score is the number of siblings.
        retval[booking.id] = len(siblings_with_high_probability)

    return retval


def find_siblings(bookings: list[Booking], camp: Camp) -> dict[BookingId, set[BookingId]]:
    """
    Find the sibling booking IDs for all bookings in the list.
    """
    # We need to find siblings who are in the queue, and also who are booked on the camp.

    # (Technically including those who already booked won't make a difference in
    # realistic situations due to other factors, but we include for completeness)

    # We are interested in getting info only for those in the current `bookings` list.
    sibling_fuzzy_ids = [b.queue_entry.sibling_fuzzy_id for b in bookings]

    # We need to get siblings "booked" or "in queue".
    # Those booked will also have a queue entry for the same camp, so we can
    # base this on BookingQueueEntry.objects.active():
    sibling_queue_entries = BookingQueueEntry.objects.active().filter(
        booking__camp=camp, sibling_fuzzy_id__in=sibling_fuzzy_ids
    )
    booking_and_sibling_ids = sibling_queue_entries.values_list("booking_id", "sibling_fuzzy_id")
    sibling_to_booking_ids_dict: dict[str, list[BookingId]] = defaultdict(list)
    for booking_id, sibling_fuzzy_id in booking_and_sibling_ids:
        sibling_to_booking_ids_dict[sibling_fuzzy_id].append(booking_id)

    # For each booking ID, get the set of *other* booking IDs that are siblings.
    booking_to_sibling_booking_ids_dict: dict[BookingId, set[BookingId]] = {}
    for booking in bookings:
        all_siblings_ids = sibling_to_booking_ids_dict.get(booking.queue_entry.sibling_fuzzy_id, [])
        non_self_siblings = set(all_siblings_ids) - set([booking.id])
        booking_to_sibling_booking_ids_dict[booking.id] = non_self_siblings
    return booking_to_sibling_booking_ids_dict


class PlacesToAllocate(PlacesLeft):
    pass


def add_queue_cutoffs(*, ranked_queue_bookings: list[Booking], places_left: PlacesLeft) -> PlacesToAllocate:
    """
    Updates the rank_info.cutoff_state field on each Booking, and returns
    a `PlacesToAllocate' object.
    """
    accepted: Counter[Literal["total"] | Sex] = Counter()
    for booking in ranked_queue_bookings:
        sex: Sex = booking.sex
        sex_limit = places_left.male if sex == Sex.MALE else places_left.female
        accepted_sex_count = accepted[sex]
        accepted_total_count = accepted["total"]
        if accepted_total_count >= places_left.total:
            cutoff = QueueCutoff.AFTER_TOTAL_CUTOFF
        elif accepted_sex_count >= sex_limit:
            cutoff = QueueCutoff.AFTER_MALE_CUTOFF if sex == Sex.MALE else QueueCutoff.AFTER_FEMALE_CUTOFF
        else:
            cutoff = QueueCutoff.ACCEPTED
            accepted[sex] += 1
            accepted["total"] += 1

        booking.rank_info.cutoff_state = cutoff

    to_allocate_bookings = [b for b in ranked_queue_bookings if b.rank_info.cutoff_state == QueueCutoff.ACCEPTED]
    places_to_allocate = PlacesToAllocate(
        total=len(to_allocate_bookings),
        male=len([b for b in to_allocate_bookings if b.sex == Sex.MALE]),
        female=len([b for b in to_allocate_bookings if b.sex == Sex.FEMALE]),
    )
    return places_to_allocate


@dataclass
class BookingQueueProblems:
    general_messages: Sequence[str]
    rejected_first_timers: Sequence[Booking]

    @property
    def has_items(self) -> bool:
        return bool(self.general_messages or self.rejected_first_timers)


def get_booking_queue_problems(*, ranked_queue_bookings: Sequence[Booking], camp: Camp) -> BookingQueueProblems:
    general_messages = []
    # If 'first timer' is allocated, they may assume that it 'works'
    rejected_first_timers = [
        b
        for b in ranked_queue_bookings
        if b.rank_info.cutoff_state != QueueCutoff.ACCEPTED and b.queue_entry.first_timer_allocated
    ]
    return BookingQueueProblems(general_messages=general_messages, rejected_first_timers=rejected_first_timers)
