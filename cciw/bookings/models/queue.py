"""
Models relating to the queue system
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

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
    created_at = models.DateTimeField(default=timezone.now)

    # TODO #52: all the fields relating to the priority rules

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
