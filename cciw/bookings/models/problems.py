from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from cciw.accounts.models import User

if TYPE_CHECKING:
    from cciw.cciwmain.models import Camp

    from .bookings import Booking


@dataclass(frozen=True, kw_only=True)
class Blocker:
    """
    Represents a problem that is a blocker for booking
    """

    description: str

    @property
    def blocker(self) -> bool:
        return True

    @property
    def fixable(self) -> bool:
        return False

    @property
    def status_display(self) -> str:
        return ""


class ApprovalNeededType(models.TextChoices):
    CUSTOM_PRICE = "custom_price", "Custom price"
    SERIOUS_ILLNESS = "serious_illness", "Serious illness"
    TOO_YOUNG = "too_young", "Too young"
    TOO_OLD = "too_old", "Too old"


ANT = ApprovalNeededType


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    DENIED = "denied", "Denied"


@dataclass(kw_only=True)
class ApprovalNeeded:
    """
    Represents booking problems that can be fixed by approval (via booking secretary)
    """

    description: str
    type: ApprovalNeededType
    booking: Booking

    linked_booking_approval: BookingApproval | None = None

    @property
    def short_description(self) -> str:
        return self.type.label

    @property
    def blocker(self) -> bool:
        if self.linked_booking_approval is not None and self.linked_booking_approval.is_approved:
            return False
        return True

    @property
    def fixable(self) -> bool:
        return True

    @property
    def status_display(self) -> str:
        if self.linked_booking_approval is None:
            return ApprovalStatus.PENDING.label
        else:
            return self.linked_booking_approval.get_status_display()

    def to_booking_approval(self) -> BookingApproval:
        if self.linked_booking_approval is not None:
            return self.linked_booking_approval
        return BookingApproval(description=self.description, type=self.type, booking=self.booking)


@dataclass(frozen=True, kw_only=True)
class Warning:
    description: str

    @property
    def blocker(self) -> bool:
        return False

    @property
    def status_display(self) -> str:
        return ""


class BookingApprovalQuerySet(models.QuerySet):
    def need_approving(self):
        return self.current().filter(status=ApprovalStatus.PENDING)

    def current(self):
        return self.filter(is_current=True)


BookingApprovalManager = models.Manager.from_queryset(BookingApprovalQuerySet)


class BookingApproval(models.Model):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="approvals")
    type = models.CharField(choices=ApprovalNeededType)
    is_current = models.BooleanField(default=True)  # soft-delete flag to avoid deleting approvals.
    status = models.CharField(choices=ApprovalStatus, default=ApprovalStatus.PENDING)
    description = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)
    checked_at = models.DateTimeField(null=True)
    checked_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name="booking_approvals")

    objects = BookingApprovalManager()

    class Meta:
        unique_together = [("booking", "type")]

    @property
    def is_approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    def __str__(self):
        return f"{self.get_type_display()}:{self.get_status_display()} for {self.booking.name}"

    @property
    def short_description(self) -> str:
        return self.get_type_display()


type BookingProblem = Blocker | ApprovalNeeded | Warning


def calculate_approvals_needed(booking: Booking) -> list[ApprovalNeeded]:
    def approval_needed(type: ANT, description: str):
        return ApprovalNeeded(type=type, description=description, booking=booking)

    approvals_needed: list[ApprovalNeeded] = []
    if booking.serious_illness:
        approvals_needed.append(
            approval_needed(ANT.SERIOUS_ILLNESS, "Must be approved by leader due to serious illness/condition")
        )
    if booking.is_custom_discount():
        approvals_needed.append(
            approval_needed(ANT.CUSTOM_PRICE, "A custom discount needs to be arranged by the booking secretary")
        )

    if booking.is_too_young() or booking.is_too_old():
        camper_age = booking.age_on_camp()
        age_base = booking.age_base_date().strftime("%e %B %Y")
        camp: Camp = booking.camp

        if booking.is_too_young():
            approvals_needed.append(
                approval_needed(
                    ANT.TOO_YOUNG,
                    f"Camper will be {camper_age} which is below the minimum age ({camp.minimum_age}) on {age_base}",
                )
            )
        elif booking.is_too_old():
            approvals_needed.append(
                approval_needed(
                    ANT.TOO_OLD,
                    f"Camper will be {camper_age} which is above the maximum age ({camp.maximum_age}) on {age_base}",
                )
            )
    return approvals_needed


def incorporate_approvals_granted(booking: Booking, approvals_needed: list[ApprovalNeeded]) -> None:
    """
    Include information from saved BookingApproval objects into the list of ApprovalNeeded object.
    """
    booking_approvals = booking.saved_current_approvals
    approvals_dict: dict[ANT, BookingApproval] = {ANT(app.type): app for app in booking_approvals}
    for app in approvals_needed:
        if app.linked_booking_approval is None:
            app.linked_booking_approval = approvals_dict.get(app.type, None)
