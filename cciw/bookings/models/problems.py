from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone
from django.utils.html import format_html

from cciw.accounts.models import User

from .constants import Sex
from .prices import PriceType
from .utils import normalise_booking_name

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

    @property
    def is_pending(self) -> bool:
        if self.linked_booking_approval is None:
            # Initial status is pending
            return True
        return self.linked_booking_approval.is_pending


@dataclass(frozen=True, kw_only=True)
class Warning:
    description: str

    @property
    def blocker(self) -> bool:
        return False

    @property
    def warning(self) -> bool:
        return True

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

    @property
    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING

    def __str__(self):
        return f"{self.get_type_display()}: {self.get_status_display()} for {self.booking.name}"

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


def get_booking_problems(
    booking: Booking, *, booking_sec: bool = False, agreement_fetcher=None
) -> list[BookingProblem]:
    return list(get_booking_errors(booking, booking_sec=booking_sec, agreement_fetcher=agreement_fetcher)) + list(
        get_booking_warnings(booking, booking_sec=booking_sec)
    )


def get_booking_errors(booking: Booking, *, booking_sec: bool = False, agreement_fetcher=None) -> list[BookingProblem]:
    errors: list[ApprovalNeeded | Blocker] = []
    camp: Camp = booking.camp

    def blocker(description: str) -> Blocker:
        return Blocker(description=description)

    approvals_needed = calculate_approvals_needed(booking)
    if booking.id is not None:
        incorporate_approvals_granted(booking, approvals_needed)
    errors.extend(approvals_needed)

    relevant_bookings = booking.account.bookings.for_year(camp.year).basket_relevant()
    relevant_bookings_excluding_self = relevant_bookings.exclude(
        fuzzy_camper_id_strict=booking.fuzzy_camper_id_strict_unsaved
    )
    relevant_bookings_limited_to_self = relevant_bookings.filter(
        fuzzy_camper_id_strict=booking.fuzzy_camper_id_strict_unsaved
    )

    # 2nd/3rd child discounts

    # 2nd child discounts are allowed when there is a full price
    # booking from the same account.
    #
    # 3rd child discounts are allowed when there are two bookings at full price/
    # or 2nd child discount from the same account.

    # When multiple camps are involved, things get complicated.
    #
    # The rule given concerning 2nd/3rd child discounts and multiple camps:
    # "A camper booking to go on a second camp will be charged at full
    # price".
    #
    # This is ambiguous and not possible to implement directly because
    # we don't know which is a camper's "first" camp and which is their "second",
    # and the logic would rely on this labelling.
    #
    # A natural interpretation of this rule is that if we have two campers
    # from the same family who both go on two camps:
    #
    # 1st child gets Full Price for first camp
    # 2nd child gets 2nd child discount for first camp
    # 1st and 2nd child both get Full Price for second camp.
    #
    # (This is different from saying "each camper may only have one 2nd/3rd
    # child discount", because that would still allow using 1 Full Price and
    # 1 2nd child discount for each child.)
    #
    # A correct re-phrasing of the rule is:
    #
    # 1. each camper may only have one discounted place
    # 2. the total number of discounted places for a family should be one less
    #    than the number of children.
    #
    # However, we can't correctly detect "same family" (broken families,
    # different surnames etc.), only "same camper", and a single account is
    # sometimes used to book multiple families. Assuming one account = one
    # family for this re-phrasing would disallow legitimate discounts.
    #
    # We cannot assume that each account will book children only from a
    # single family, but we will assume that all children from a family will
    # be booked by the same account, which is a reasonable constraint, and
    # matches how bookings are actually done.
    #
    # With these facts in mind, we rephrase the rule:
    #
    # 1. each camper may only have one discounted place
    # 2. 2nd child discounts can only be given if there are at least
    #    2 different children booked by an account
    # 3. 3rd child discounts can only be given if there are at least
    #    3 different children booked by an account
    #
    # This is not exactly correct, but allows all legitimate discounts.

    if booking.price_type == PriceType.SECOND_CHILD:
        if not (relevant_bookings_excluding_self.filter(price_type=PriceType.FULL)).exists():
            errors.append(
                blocker(
                    "You cannot use a 2nd child discount unless you have "
                    "another child at full price. Please edit the place details "
                    "and choose an appropriate price type."
                )
            )

    if booking.price_type == PriceType.THIRD_CHILD:
        qs = relevant_bookings_excluding_self.filter(
            price_type=PriceType.FULL
        ) | relevant_bookings_excluding_self.filter(price_type=PriceType.SECOND_CHILD)
        if qs.count() < 2:
            errors.append(
                blocker(
                    "You cannot use a 3rd child discount unless you have "
                    "two other children without this discount. Please edit the "
                    "place details and choose an appropriate price type."
                )
            )

    if booking.price_type in [PriceType.SECOND_CHILD, PriceType.THIRD_CHILD]:
        qs = relevant_bookings_limited_to_self
        qs = qs.filter(price_type=PriceType.SECOND_CHILD) | qs.filter(price_type=PriceType.THIRD_CHILD)
        if qs.count() > 1:
            errors.append(
                blocker("If a camper goes on multiple camps, only one place may use a 2nd/3rd child discount.")
            )

    if booking.south_wales_transport and not camp.south_wales_transport_available:
        errors.append(
            blocker("Transport from South Wales is not available for this camp, or all places have been taken already.")
        )

    if booking_sec and booking.price_type != PriceType.CUSTOM:
        expected_amount = booking.expected_amount_due()
        if booking.amount_due != expected_amount:
            errors.append(blocker(f"The 'amount due' is not the expected value of £{expected_amount}."))

    if booking_sec and not booking.created_online:
        if booking.early_bird_discount:
            errors.append(blocker("The early bird discount is only allowed for bookings created online."))

    # Don't want warnings for booking sec when a booked place is edited
    # after the cutoff date, so we allow self.booked_at to be used here:
    on_date: date = booking.booked_at if booking.is_booked and booking.booked_at is not None else date.today()

    if not camp.open_for_bookings(on_date):
        if on_date >= camp.end_date:
            msg = "This camp has already finished."
        elif on_date >= camp.start_date:
            msg = "This camp is closed for bookings because it has already started."
        else:
            msg = "This camp is closed for bookings."
        errors.append(blocker(msg))

    missing_agreements = booking.get_missing_agreements(agreement_fetcher=agreement_fetcher)
    for agreement in missing_agreements:
        errors.append(blocker(f'You need to confirm your agreement in section "{agreement.name}"'))

    return errors


def get_booking_warnings(booking: Booking, *, booking_sec: bool = False) -> list[BookingProblem]:
    camp: Camp = booking.camp
    warnings: list[str] = []

    relevant_bookings = booking.account.bookings.for_year(camp.year).basket_relevant()
    relevant_bookings_limited_to_self = relevant_bookings.filter(
        fuzzy_camper_id_strict=booking.fuzzy_camper_id_strict_unsaved
    )

    if relevant_bookings_limited_to_self.filter(camp=camp).exclude(id=booking.id):
        warnings.append(
            f"You have entered another set of place details for a camper "
            f"called '{booking.name}' on camp {camp.name}. Please ensure you don't book multiple "
            f"places for the same camper!"
        )

    if booking.price_type == PriceType.FULL:
        full_pricers = relevant_bookings.filter(price_type=PriceType.FULL)
        unique_names = {normalise_booking_name(b) for b in full_pricers}
        if len(unique_names) > 1:
            # Use original names for printing message
            names = sorted({b.name for b in full_pricers})
            pretty_names = ", ".join(names[1:]) + " and " + names[0]
            warning = "You have multiple places at 'Full price'. "
            if len(names) == 2:
                warning += f"If {pretty_names} are from the same family, one is eligible for the 2nd child discount."
            else:
                warning += f"If {pretty_names} are from the same family, one or more is eligible for the 2nd or 3rd child discounts."

            warnings.append(warning)

    if booking.price_type == PriceType.SECOND_CHILD:
        second_childers = relevant_bookings.filter(price_type=PriceType.SECOND_CHILD)
        unique_names = sorted({normalise_booking_name(b) for b in second_childers})
        if len(unique_names) > 1:
            # Use original names for printing message
            names = sorted({b.name for b in second_childers})
            pretty_names = ", ".join(names[1:]) + " and " + names[0]
            warning = "You have multiple places at '2nd child discount'. "
            if len(names) == 2:
                warning += f"If {pretty_names} are from the same family, one is eligible for the 3rd child discount."
            else:
                warning += (
                    f"If {pretty_names} are from the same family, {len(names) - 1} are eligible "
                    f"for the 3rd child discount."
                )

            warnings.append(warning)

    # Check place availability
    places_left = camp.get_places_left()

    # We only want one message about places not being available, and the
    # order here is important - if there are no places full stop, we don't
    # want to display message about there being no places for boys etc.
    places_available = True

    def no_places_available_message(msg: str) -> str:
        # Add a common message to each different "no places available" message
        return format_html(
            """{0}
            You will be placed on the waiting list if you book now.""",
            msg,
        )

    # Simple - no places left
    if places_left.total <= 0:
        warnings.append(no_places_available_message("There are no places left on this camp."))
        places_available = False

    SEXES = [
        (Sex.MALE, "boys", places_left.male),
        (Sex.FEMALE, "girls", places_left.female),
    ]

    if places_available:
        for sex_const, sex_label, places_left_for_sex in SEXES:
            if booking.sex == sex_const and places_left_for_sex <= 0:
                warnings.append(no_places_available_message(f"There are no places left for {sex_label} on this camp."))
                places_available = False
                break

    if places_available:
        # Complex - need to check the other places that are about to be booked.
        # (if there is one place left, and two campers for it, we can't say that
        # there are enough places)
        same_camp_bookings = booking.account.bookings.filter(camp=camp).in_basket()
        places_to_be_booked = len(same_camp_bookings)

        if places_left.total < places_to_be_booked:
            warnings.append(
                no_places_available_message(
                    "There are not enough places left on this camp for the campers in this set of bookings."
                )
            )
            places_available = False

        if places_available:
            for sex_const, sex_label, places_left_for_sex in SEXES:
                if booking.sex == sex_const:
                    places_to_be_booked_for_sex = len([b for b in same_camp_bookings if b.sex == sex_const])
                    if places_left_for_sex < places_to_be_booked_for_sex:
                        warnings.append(
                            no_places_available_message(
                                f"There are not enough places for {sex_label} left on this camp "
                                "for the campers in this set of bookings."
                            )
                        )
                        places_available = False
                        break

    # Same person on multiple camps.
    if relevant_bookings_limited_to_self.aggregate(count=models.Count("camp"))["count"] > 1:
        warnings.append(
            f'You are trying to book places for "{booking.name}" on more than one camp. '
            + "This will result in one place having low priority and being unlikely to get allocated, but we cannot gaurantee which one."
        )

    return [Warning(description=warning) for warning in warnings]
