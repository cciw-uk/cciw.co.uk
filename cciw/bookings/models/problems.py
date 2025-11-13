from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from cciw.accounts.models import User

if TYPE_CHECKING:
    from .bookings import Booking


@dataclass(frozen=True, kw_only=True)
class Blocker:
    description: str

    @property
    def blocker(self) -> bool:
        return True

    @property
    def fixable(self) -> bool:
        return False


class ApprovalNeededType(models.TextChoices):
    CUSTOM_PRICE = "custom_price", "Custom price"
    SERIOUS_ILLNESS = "serious_illness", "Serious illness"
    TOO_YOUNG = "too_young", "Too young"
    TOO_OLD = "too_old", "Too old"


ANT = ApprovalNeededType


@dataclass(frozen=True, kw_only=True)
class ApprovalNeeded:
    """
    Represents booking problems that can be fixed by approval (via booking secretary)
    """

    description: str
    type: ApprovalNeededType
    booking: Booking

    @property
    def short_description(self) -> str:
        return self.type.label

    @property
    def blocker(self) -> bool:
        return True

    @property
    def fixable(self) -> bool:
        return True

    def to_booking_approval(self) -> BookingApproval:
        return BookingApproval(description=self.description, type=self.type, booking=self.booking)


@dataclass(frozen=True, kw_only=True)
class Warning:
    description: str

    @property
    def blocker(self) -> bool:
        return False


class BookingApprovalQuerySet(models.QuerySet):
    def need_approving(self):
        return self.current().filter(approved_at__isnull=True)

    def current(self):
        return self.filter(is_current=True)


BookingApprovalManager = models.Manager.from_queryset(BookingApprovalQuerySet)


class BookingApproval(models.Model):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="approvals")
    type = models.CharField(choices=ApprovalNeededType)
    is_current = models.BooleanField(default=True)  # soft-delete flag to avoid deleting approvals.
    description = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True)
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name="booking_approvals")

    objects = BookingApprovalManager()

    @property
    def is_approved(self) -> bool:
        return self.approved_at is not None

    def __str__(self):
        return f"{self.get_type_display()} for {self.booking.name}"

    @property
    def short_description(self) -> str:
        return self.get_type_display()


type BookingProblem = Blocker | ApprovalNeeded | Warning
