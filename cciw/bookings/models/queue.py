"""
Models relating to the queue system
"""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Literal

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Count, OuterRef, Subquery, Value, functions
from django.db.models.enums import TextChoices
from django.utils import timezone

from cciw.accounts.models import User
from cciw.bookings.models.accounts import BookingAccount
from cciw.bookings.models.constants import Sex
from cciw.bookings.models.yearconfig import YearConfig, get_year_config
from cciw.cciwmain.models import Camp, PlacesBooked, PlacesLeft
from cciw.utils.functional import partition

from .states import BookingState

if TYPE_CHECKING:
    from .bookings import Booking, BookingQuerySet


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

    def for_camp(self, camp: Camp):
        return self.filter(booking__camp=camp)


class BookingQueueEntryManagerBase(models.Manager):
    def create_for_booking(self, booking: Booking, *, by_user: User | BookingAccount) -> BookingQueueEntry:
        queue_entry: BookingQueueEntry = self.create(
            booking=booking,
            is_active=True,
            sibling_surname=booking.last_name,
            sibling_booking_account=booking.account,
        )
        queue_entry.save_action_log(action_type=QueueEntryActionLogType.CREATED, by_user=by_user)
        return queue_entry


BookingQueueEntryManager = BookingQueueEntryManagerBase.from_queryset(BookingQueueEntryQuerySet)


class BookingQueueEntry(models.Model):
    booking = models.OneToOneField(to="bookings.Booking", on_delete=models.CASCADE, related_name="queue_entry")

    # We avoid deleting queue entries, so that our auditing etc. works
    # better, so we have this soft-delete function instead.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Fields relating to priority rules:

    # enqueued_at can be different from created_at if they were removed from the queue
    # (by making `is_active` False)
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
        db_index=True,
    )

    # A queue entry is marked 'waiting_list_from_start' if it was clear from
    # the start that it would go into the waiting list, not into the queue
    # that might be accepted or declined.
    waiting_list_from_start = models.BooleanField(default=False)

    # Internal only:
    declined_notification_sent_at = models.DateTimeField(null=True, blank=True, default=None)
    accepted_notification_sent_at = models.DateTimeField(null=True, blank=True, default=None)
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

    @contextmanager
    def track_changes(self, *, by_user: User | BookingAccount) -> Iterator[None]:
        old_queue_entry_fields = self.get_current_field_data()
        yield
        self.save_fields_changed_action_log(by_user=by_user, old_fields=old_queue_entry_fields)

    def get_current_field_data(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    def save_fields_changed_action_log(
        self, *, by_user: User | BookingAccount, old_fields: dict
    ) -> QueueEntryActionLog:
        new_fields = self.get_current_field_data()
        changed: list[dict] = []
        for key, value in new_fields.items():
            old_value = old_fields[key]
            if old_value != value:
                changed.append({"name": key, "old_value": old_value, "new_value": value})
        details = {"fields_changed": changed}
        return self.save_action_log(
            by_user=by_user,
            action_type=QueueEntryActionLogType.FIELDS_CHANGED,
            details=details,
        )

    def save_action_log(
        self, *, action_type: QueueEntryActionLogType, by_user: User | BookingAccount, details: dict | None = None
    ) -> QueueEntryActionLog:
        account_user: BookingAccount | None = by_user if isinstance(by_user, BookingAccount) else None
        staff_user: User | None = by_user if isinstance(by_user, User) else None

        assert account_user or staff_user
        details = details or {}
        return self.action_logs.create(
            account_user=account_user, staff_user=staff_user, action_type=action_type, details=details
        )

    objects = BookingQueueEntryManager()

    class Meta:
        verbose_name = "queue entry"
        verbose_name_plural = "queue entries"

    def __str__(self):
        return f"Queue entry for {self.booking.name}"

    def make_active(self, *, by_user: User | BookingAccount) -> None:
        if not self.is_active:
            with self.track_changes(by_user=by_user):
                self.is_active = True
                self.enqueued_at = timezone.now()
                self.save()

    def make_inactive(self, *, by_user: User | BookingAccount) -> None:
        if self.is_active:
            with self.track_changes(by_user=by_user):
                self.is_active = False
                self.save()

    @property
    def has_been_sent_declined_notification(self) -> bool:
        return self.declined_notification_sent_at is not None


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
    has_other_place_in_queue: bool
    has_other_place_booked: bool
    cutoff_state: QueueCutoff = QueueCutoff.UNDECIDED


class QueueEntryActionLogType(TextChoices):
    FIELDS_CHANGED = "fields_changed", "fields changed"
    CREATED = "created", "created"

    # This is when they are allocated a place (becomes 'booked')
    # using the normal queue mechanism
    ALLOCATED = "allocated", "allocated"

    # When they are not allocated a place, and are notified.
    DECLINED = "declined", "declined"


class QueueEntryActionLog(models.Model):
    queue_entry = models.ForeignKey(BookingQueueEntry, related_name="action_logs", on_delete=models.CASCADE)
    action_type = models.CharField(choices=QueueEntryActionLogType)
    created_at = models.DateTimeField(default=timezone.now)
    staff_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="queue_entry_actions_performed",
        null=True,
        blank=True,
        default=None,
        help_text="The staff user that triggered the action",
    )
    account_user = models.ForeignKey(
        "bookings.BookingAccount",
        on_delete=models.PROTECT,
        related_name="queue_entry_actions_performed",
        null=True,
        blank=True,
        default=None,
        help_text="The booking account that triggered the action",
    )

    details = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)


@dataclass
class RankingResult:
    """
    Results from get_camp_booking_queue_ranking_result:
    - bookings with populated `.rank_info` attributes
    - other related info
    """

    bookings: list[Booking]  # with .rank_info objects TODO nicer type for this
    problems: BookingQueueProblems
    ready_to_allocate: PlacesToAllocate

    # Summary of current stats, before allocation:
    places_booked: PlacesBooked
    places_left: PlacesLeft


def get_camp_booking_queue_ranking_result(*, camp: Camp, year_config: YearConfig) -> RankingResult:
    """
    The main entry point for view functions - get ranking of bookings.
    """
    places_booked = camp.get_places_booked()
    places_left = camp.get_places_left(booked=places_booked)
    ranked_queue_bookings = rank_queue_bookings(camp=camp, year_config=year_config)
    ready_to_allocate = add_queue_cutoffs(ranked_queue_bookings=ranked_queue_bookings, places_left=places_left)
    problems = get_booking_queue_problems(ranked_queue_bookings=ranked_queue_bookings, camp=camp)

    # We also return some other info needed by the main view functions:
    return RankingResult(
        bookings=ranked_queue_bookings,
        places_booked=places_booked,
        places_left=places_left,
        ready_to_allocate=ready_to_allocate,
        problems=problems,
    )


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

    queue_bookings.sort(key=ranking_key)
    return list(queue_bookings)


def ranking_key(booking: Booking) -> tuple:
    is_officer_child_key = 0 if booking.queue_entry.officer_child else 1
    first_timer_key = 0 if booking.queue_entry.first_timer_allocated else 1
    has_other_place_booked_key = 1 if booking.rank_info.has_other_place_booked else 0
    queue_position_key: int = booking.rank_info.queue_position_rank
    # More attendance is better:
    previous_attendance_key: int = -booking.rank_info.previous_attendance_score
    # In the list means higher priority:
    previous_year_waiting_list_key = 0 if booking.rank_info.in_previous_year_waiting_list else 1
    # More siblings is better:
    sibling_bonus_key: int = -booking.rank_info.sibling_bonus
    tiebreaker_key: int = booking.queue_entry.tiebreaker

    return (
        is_officer_child_key,
        first_timer_key,
        has_other_place_booked_key,
        queue_position_key,
        previous_attendance_key,
        previous_year_waiting_list_key,
        sibling_bonus_key,
        tiebreaker_key,
    )


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
    other_places_in_queue: dict[BookingId, int] = get_other_places_in_queue(bookings, camp)
    other_places_booked: dict[BookingId, int] = get_other_places_booked(bookings, camp)
    for booking in bookings:
        booking.rank_info = RankInfo(
            queue_position_rank=queue_position_ranks[booking.id],
            # score is currently the same as the count - the more attendance,
            # the better.
            previous_attendance_score=attendance_counts[booking.id],
            in_previous_year_waiting_list=in_previous_year_waiting_list_info[booking.id],
            sibling_bonus=sibling_bonus_scores[booking.id],
            has_other_place_in_queue=other_places_in_queue[booking.id] > 0,
            has_other_place_booked=other_places_booked[booking.id] > 0,
        )


def get_queue_position_ranks(bookings: list[Booking], year_config: YearConfig):
    """
    Define 'queue_position_ranks', based on 'queue_position' and the initial booking period.
    """

    # Everyone booked within the initial period is first equal,
    # everyone later is in ascending order.

    def is_in_initial_period(booking: Booking) -> bool:
        return booking.queue_entry.enqueued_at.date() <= year_config.bookings_close_for_initial_period_on

    def initial_sort_key(booking: Booking) -> tuple:
        # Those in initial period should come first
        return (not is_in_initial_period(booking), booking.queue_entry.enqueued_at)

    # Sort so that those in the initial period are first,
    # the rest are in order of their `enqueued_at`
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


def get_other_places_in_queue(bookings: Sequence[Booking], camp: Camp) -> dict[BookingId, int]:
    """
    Gets counts of bookings that have other places in queue for the same camper but different camp.
    """
    from cciw.bookings.models import Booking

    # We can do a simpler query by starting with a new QuerySet:
    this_camp_bookings = Booking.objects.for_camp(camp).in_queue()
    other_camp_bookings = Booking.objects.for_year(camp.year).in_queue().exclude(camp=camp)
    with_matches = this_camp_bookings.annotate(
        other_places_count=Subquery(
            other_camp_bookings.filter(fuzzy_camper_id_strict=OuterRef("fuzzy_camper_id_strict"))
            .values("fuzzy_camper_id_strict")
            .annotate(c=Count("id"))
            .values("c"),
            output_field=models.IntegerField(),
        )
    ).values("id", "other_places_count")
    with_matches_dict: dict[BookingId, int] = {b["id"]: b["other_places_count"] or 0 for b in with_matches}
    for booking in bookings:
        assert booking.id in with_matches_dict
    return with_matches_dict


def get_other_places_booked(bookings: Sequence[Booking], camp: Camp) -> dict[BookingId, int]:
    """
    Gets counts of bookings that other places booked for the same camper but different camp.
    """
    from cciw.bookings.models import Booking

    # Similar to above, but for actually booked places.
    # We use fuzzy_camper_id_strict here (and above), because false positives for matching
    # have a very strong negative effect on priority
    this_camp_bookings = Booking.objects.for_camp(camp).in_queue()
    other_camp_bookings = Booking.objects.for_year(year=camp.year).booked().exclude(camp=camp)
    with_matches = this_camp_bookings.annotate(
        other_places_count=Subquery(
            other_camp_bookings.filter(fuzzy_camper_id_strict=OuterRef("fuzzy_camper_id_strict"))
            .values("fuzzy_camper_id_strict")
            .annotate(c=Count("id"))
            .values("c"),
            output_field=models.IntegerField(),
        )
    ).values("id", "other_places_count")
    with_matches_dict: dict[BookingId, int] = {b["id"]: b["other_places_count"] or 0 for b in with_matches}
    for booking in bookings:
        assert booking.id in with_matches_dict
    return with_matches_dict


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
    rejected_officer_children: Sequence[Booking]
    rejected_first_timers: Sequence[Booking]

    @property
    def has_items(self) -> bool:
        return bool(self.general_messages or self.rejected_officer_children or self.rejected_first_timers)


def get_booking_queue_problems(*, ranked_queue_bookings: Sequence[Booking], camp: Camp) -> BookingQueueProblems:
    general_messages = []
    # If 'officer child' or 'first timer' is allocated, they may assume that it 'works'
    # so we add a warning if it hasn't.
    rejected_officer_children = [
        b
        for b in ranked_queue_bookings
        if b.rank_info.cutoff_state != QueueCutoff.ACCEPTED and b.queue_entry.officer_child
    ]
    rejected_first_timers = [
        b
        for b in ranked_queue_bookings
        if b.rank_info.cutoff_state != QueueCutoff.ACCEPTED and b.queue_entry.first_timer_allocated
    ]

    # Check the number of first timers is within limits.
    # We use `camp` for this query, not `ranked_queue_bookings`, because we need to include
    # bookings that have already been accepted and are no longer in ranked_queue_bookings
    first_timer_count = BookingQueueEntry.objects.for_camp(camp).filter(first_timer_allocated=True).count()
    total_places = camp.max_campers
    allowed_first_timers = math.ceil(total_places / FIRST_TIMER_PERCENTAGE)
    if first_timer_count > allowed_first_timers:
        general_messages.append(
            f'{first_timer_count} bookings are marked as "chosen first timers", but only {allowed_first_timers} are allowed ({FIRST_TIMER_PERCENTAGE}%)'
        )

    return BookingQueueProblems(
        general_messages=general_messages,
        rejected_officer_children=rejected_officer_children,
        rejected_first_timers=rejected_first_timers,
    )


@dataclass(frozen=True)
class AllocationResult:
    accepted_booking_count: int
    accepted_account_count: int
    declined_and_notified_account_count: int


def allocate_places_and_notify(
    ranked_queue_bookings: Sequence[Booking], *, by_user: User | BookingAccount
) -> AllocationResult:
    from cciw.bookings.email import send_places_allocated_email, send_places_declined_email

    by_account_key: Callable[[Booking], BookingAccount] = lambda b: b.account
    by_account_id_key: Callable[[Booking], int] = lambda b: b.account_id

    # Sort bookings by account ID so that group by works
    ranked_queue_bookings = sorted(ranked_queue_bookings, key=by_account_id_key)
    to_book, to_decline = partition(
        ranked_queue_bookings, key=lambda b: b.rank_info.cutoff_state == QueueCutoff.ACCEPTED
    )

    # Allocate:
    book_bookings_now(to_book)
    for booking in to_book:
        booking.queue_entry.save_action_log(action_type=QueueEntryActionLogType.ALLOCATED, by_user=by_user)

    to_book_grouped_by_account = [(a, list(g)) for a, g in itertools.groupby(to_book, key=by_account_key)]
    for account, bookings in to_book_grouped_by_account:
        send_places_allocated_email(account, bookings)

    # Decline:
    to_decline_and_notify = [b for b in to_decline if not b.queue_entry.has_been_sent_declined_notification]
    for booking in to_decline_and_notify:
        # We only add a 'DECLINED' action when they are notified as well,
        # because "declining" happens implicitly every time they are passed over
        # by the allocation process, and we don't need to log that every time.
        # (we possibly don't need to log it at all)
        booking.queue_entry.save_action_log(action_type=QueueEntryActionLogType.DECLINED, by_user=by_user)

    to_decline_and_notify_grouped_by_account = [
        (a, list(g)) for a, g in itertools.groupby(to_decline_and_notify, key=by_account_key)
    ]

    for account, bookings in to_decline_and_notify_grouped_by_account:
        send_places_declined_email(account, bookings)

    return AllocationResult(
        accepted_booking_count=len(to_book),
        accepted_account_count=len(to_book_grouped_by_account),
        declined_and_notified_account_count=len(to_decline_and_notify_grouped_by_account),
    )


def book_bookings_now(bookings_qs: BookingQuerySet | list[Booking]):
    """
    Book a group of bookings.
    """
    # TODO #52 - this is used by tests currently,
    # we probably want something that operates on BookingQueueEntry objects
    # and changes the `state` value.
    bookings: list[Booking] = list(bookings_qs)

    now = timezone.now()

    for b in bookings:
        b.booked_at = now
        # Early bird discounts are only applied for online bookings, and
        # this needs to be re-assessed if a booking expires and is later
        # booked again. Therefore it makes sense to put the logic here
        # rather than in the Booking model.
        b.early_bird_discount = b.can_have_early_bird_discount()
        b.auto_set_amount_due()
        b.state = BookingState.BOOKED
        b.save()

    return True
