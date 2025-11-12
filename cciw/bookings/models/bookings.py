from __future__ import annotations

import contextlib
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.utils.models import AfterFetchQuerySetMixin

from .accounts import BookingAccount
from .agreements import AgreementFetcher, CustomAgreement
from .constants import DEFAULT_COUNTRY
from .prices import BOOKING_PLACE_PRICE_TYPES, Price, PriceChecker, PriceType
from .problems import ApprovalNeeded, ApprovalNeededType, Blocker, BookingApproval, BookingProblem, Warning
from .states import BookingState
from .utils import early_bird_is_available

if TYPE_CHECKING:
    from .problems import BookingApproval

ANT = ApprovalNeededType


class Sex(models.TextChoices):
    MALE = "m", "Male"
    FEMALE = "f", "Female"


class Array(models.Func):
    function = "ARRAY"


class BookingQuerySet(AfterFetchQuerySetMixin, models.QuerySet):
    def for_year(self, year):
        return self.filter(camp__year__exact=year)

    def in_basket(self):
        return self._ready_to_book(shelved=False)

    def on_shelf(self):
        return self._ready_to_book(shelved=True)

    def _ready_to_book(self, *, shelved):
        qs = self.filter(shelved=shelved)
        return qs.filter(state=BookingState.INFO_COMPLETE) | qs.filter(state=BookingState.APPROVED)

    def booked(self):
        return self.filter(state=BookingState.BOOKED)

    def in_basket_or_booked(self):
        return self.in_basket() | self.booked()

    def confirmed(self):
        return self.filter(state=BookingState.BOOKED, booking_expires_at__isnull=True)

    def unconfirmed(self):
        return self.filter(state=BookingState.BOOKED, booking_expires_at__isnull=False)

    def payable(self, *, confirmed_only: bool):
        """
        Returns bookings for which payment is expected.
        If confirmed_only is True, unconfirmed places are excluded.
        """
        # See also:
        #   Booking.is_payable()

        # Also booking_secretary_reports has overlapping logic.

        # 'Full refund' cancelled bookings do not have payment expected, but the
        # others do.
        return self.filter(state__in=[BookingState.CANCELLED_DEPOSIT_KEPT, BookingState.CANCELLED_HALF_REFUND]) | (
            self.confirmed() if confirmed_only else self.booked()
        )

    def cancelled(self):
        return self.filter(
            state__in=[
                BookingState.CANCELLED_DEPOSIT_KEPT,
                BookingState.CANCELLED_HALF_REFUND,
                BookingState.CANCELLED_FULL_REFUND,
            ]
        )

    def with_approvals(self) -> QuerySet[Booking]:
        return self.prefetch_related("approvals")

    def need_approving(self):
        """
        Returns Bookings that need approving
        """
        qs = self.filter(state=BookingState.INFO_COMPLETE).select_related("camp")
        approvals_booking_ids_qs = BookingApproval.objects.need_approving().values_list("booking_id", flat=True)
        qs = qs.filter(id__in=approvals_booking_ids_qs)
        return qs

    def future(self):
        return self.filter(camp__start_date__gt=date.today())

    def missing_agreements(self):
        """
        Returns bookings that are missing agreements.
        """
        # This typically happens if a CustomAgreement was addded after the place
        # was booked.

        # See also Booking.get_missing_agreements()
        return self.exclude(self._agreements_complete_Q())

    def no_missing_agreements(self):
        return self.filter(self._agreements_complete_Q())

    def _agreements_complete_Q(self):
        return Q(
            custom_agreements_checked__contains=Array(
                CustomAgreement.objects.active().for_year(models.OuterRef("camp__year")).values_list("id")
            )
        )

    def agreement_fix_required(self):
        # We need a fix if:
        # - it is booked
        # - it is missing an agreement
        # - it is a future camp. For past camps, there is nothing we can do about it.
        return self.booked().missing_agreements().future()

    # Performance
    def with_prefetch_camp_info(self):
        return self.select_related(
            "camp",
            "camp__camp_name",
            "camp__chaplain",
        ).prefetch_related(
            "camp__leaders",
        )

    def with_prefetch_missing_agreements(self, agreement_fetcher):
        def add_missing_agreements(booking_list):
            for booking in booking_list:
                booking.missing_agreements = booking.get_missing_agreements(agreement_fetcher=agreement_fetcher)

        return self.register_after_fetch_callback(add_missing_agreements)

    # Data retention

    def not_in_use(self, now: datetime):
        return self.exclude(self._in_use_q(now))

    def in_use(self, now: datetime):
        return self.filter(self._in_use_q(now))

    def _in_use_q(self, now: datetime):
        return Q(
            camp__end_date__gte=now.date(),
        )

    def older_than(self, before_datetime):
        return self.filter(
            Q(created_at__lt=before_datetime) & Q(Q(camp__isnull=True) | Q(camp__end_date__lt=before_datetime))
        )

    def non_erased(self):
        return self.filter(erased_at__isnull=True)


class BookingManagerBase(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("camp", "account")


BookingManager = BookingManagerBase.from_queryset(BookingQuerySet)


class Booking(models.Model):
    """
    Information regarding a camper's place on a camp.
    """

    account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="bookings")

    # Booking details - from user
    camp = models.ForeignKey(Camp, on_delete=models.PROTECT, related_name="bookings")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=Sex)
    birth_date = models.DateField("date of birth")
    address_line1 = models.CharField("address line 1", max_length=255)
    address_line2 = models.CharField("address line 2", max_length=255, blank=True)
    address_city = models.CharField("town/city", max_length=255)
    address_county = models.CharField("county/state", max_length=255, blank=True)
    address_country = CountryField("country", null=True, default=DEFAULT_COUNTRY)
    address_post_code = models.CharField("post code", max_length=10)

    phone_number = models.CharField(blank=True, max_length=22)
    email = models.EmailField(blank=True)
    church = models.CharField("name of church", max_length=100, blank=True)
    south_wales_transport = models.BooleanField("require transport from South Wales", blank=True, default=False)

    # Contact - from user
    contact_name = models.CharField("contact name", max_length=255, blank=True)
    contact_line1 = models.CharField("address line 1", max_length=255)
    contact_line2 = models.CharField("address line 2", max_length=255, blank=True)
    contact_city = models.CharField("town/city", max_length=255)
    contact_county = models.CharField("county/state", max_length=255, blank=True)
    contact_country = CountryField("country", null=True, default=DEFAULT_COUNTRY)
    contact_post_code = models.CharField("post code", max_length=10)
    contact_phone_number = models.CharField(max_length=22)

    # Diet - from user
    dietary_requirements = models.TextField(blank=True)

    # GP details - from user
    gp_name = models.CharField("GP name", max_length=100)
    gp_line1 = models.CharField("address line 1", max_length=255)
    gp_line2 = models.CharField("address line 2", max_length=255, blank=True)
    gp_city = models.CharField("town/city", max_length=255)
    gp_county = models.CharField("county/state", max_length=255, blank=True)
    gp_country = CountryField("country", null=True, default=DEFAULT_COUNTRY)
    gp_post_code = models.CharField("post code", max_length=10)
    gp_phone_number = models.CharField("GP phone number", max_length=22)

    # Medical details - from user
    medical_card_number = models.CharField("NHS number", max_length=100)  # no idea how long it should be
    last_tetanus_injection_date = models.DateField(null=True, blank=True)
    allergies = models.TextField(blank=True)
    regular_medication_required = models.TextField(blank=True)
    illnesses = models.TextField("Medical conditions", blank=True)
    can_swim_25m = models.BooleanField(blank=True, default=False, verbose_name="Can the camper swim 25m?")
    learning_difficulties = models.TextField(blank=True)
    serious_illness = models.BooleanField(blank=True, default=False)

    # Other
    friends_for_tent_sharing = models.CharField(max_length=1000, blank=True, default="")

    # Agreement - from user
    agreement = models.BooleanField(default=False)
    publicity_photos_agreement = models.BooleanField(default=False, blank=True)

    # Custom agreements: Array of CustomAgreement.id integers, for the
    # CustomAgreements that the booker has agreed to.
    # This schema choice is based on:
    # - need to be able to query for this in missing_agreements()
    # - we only ever update this as a single field, we never need to
    #   treat it as a table.
    custom_agreements_checked = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="Comma separated list of IDs of custom agreements the user has agreed to.",
    )

    # Price - partly from user (must fit business rules)
    price_type = models.PositiveSmallIntegerField(choices=[(pt, pt.label) for pt in BOOKING_PLACE_PRICE_TYPES])
    early_bird_discount = models.BooleanField(default=False, help_text="Online bookings only")
    booked_at = models.DateTimeField(null=True, blank=True, help_text="Online bookings only")
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - user driven
    shelved = models.BooleanField(default=False, help_text="Used by user to put on 'shelf'")

    # State - internal
    state = models.CharField(
        choices=BookingState,
        help_text=mark_safe(
            "<ul>"
            "<li>To book, set to 'Booked' <b>and</b> ensure 'Booking expires' is empty</li>"
            "<li>For people paying online who have been stopped (e.g. due to having a custom discount or serious illness or child too young etc.), set to 'Manually approved' to allow them to book and pay</li>"
            "<li>If there are queries before it can be booked, set to 'Information complete'</li>"
            "</ul>"
        ),
    )

    created_at = models.DateTimeField(default=timezone.now)
    booking_expires_at = models.DateTimeField(null=True, blank=True)
    created_online = models.BooleanField(blank=True, default=False)

    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = BookingManager()

    class Meta:
        ordering = ["-created_at"]
        base_manager_name = "objects"

    # Methods

    def __str__(self):
        return f"{self.name}, {self.camp.url_id}, {self.account}"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    # Main business rules here
    def save_for_account(
        self, *, account: BookingAccount, state_was_booked: bool, custom_agreements: list[CustomAgreement] = None
    ):
        """
        Saves the booking for an account that is creating/editing online
        """
        self.account = account
        if not state_was_booked:
            self.early_bird_discount = False  # We only allow this to be True when booking
            self.state = BookingState.INFO_COMPLETE
        self.auto_set_amount_due()
        if self.id is None:
            self.created_online = True
        if custom_agreements is not None:
            self.custom_agreements_checked = [agreement.id for agreement in custom_agreements]
        self.save()
        self.update_approvals()

    def is_payable(self, *, confirmed_only: bool) -> bool:
        # See also BookingQuerySet.payable()
        return self.state in [BookingState.CANCELLED_DEPOSIT_KEPT, BookingState.CANCELLED_HALF_REFUND] or (
            self.is_confirmed if confirmed_only else self.is_booked
        )

    @property
    def is_booked(self) -> bool:
        return self.state == BookingState.BOOKED

    @property
    def is_confirmed(self) -> bool:
        return self.is_booked and self.booking_expires_at is None

    def expected_amount_due(self) -> Decimal | None:
        if self.price_type == PriceType.CUSTOM:
            return None
        if self.state == BookingState.CANCELLED_DEPOSIT_KEPT:
            return Price.objects.get(year=self.camp.year, price_type=PriceType.DEPOSIT).price
        elif self.state == BookingState.CANCELLED_FULL_REFUND:
            return Decimal("0.00")
        else:
            amount = Price.objects.get(year=self.camp.year, price_type=self.price_type).price
            # For booking 2015 and later, this is not needed, but it kept in
            # case we need to query the expected amount due for older bookings.
            if self.south_wales_transport:
                amount += Price.objects.get(price_type=PriceType.SOUTH_WALES_TRANSPORT, year=self.camp.year).price

            if self.early_bird_discount:
                amount -= Price.objects.get(price_type=PriceType.EARLY_BIRD_DISCOUNT, year=self.camp.year).price

            # For booking 2015 and later, there are no half refunds,
            # but this is kept in in case we need to query the expected amount due for older
            # bookings.
            if self.state == BookingState.CANCELLED_HALF_REFUND:
                amount = amount / 2

            return amount

    def auto_set_amount_due(self) -> None:
        amount = self.expected_amount_due()
        if amount is None:
            # This happens for PriceType.CUSTOM
            if self.amount_due is None:
                self.amount_due = Decimal("0.00")
            # Otherwise - should leave as it was.
        else:
            self.amount_due = amount

    def amount_now_due(self, today: date, *, allow_deposits, price_checker: PriceChecker) -> Decimal:
        # Amount due at this point of time. If allow_deposits=True, we take into
        # account the fact that only a deposit might be due. Otherwise we ignore
        # deposits (which means that the current date is also ignored)
        cutoff = today + settings.BOOKING_FULL_PAYMENT_DUE
        if allow_deposits and self.camp.start_date > cutoff:
            deposit_price = price_checker.get_deposit_price(self.camp.year)
            return min(deposit_price, self.amount_due)
        return self.amount_due

    def can_have_early_bird_discount(self, booked_at=None):
        if booked_at is None:
            booked_at = self.booked_at
        if self.price_type == PriceType.CUSTOM:
            return False
        else:
            return early_bird_is_available(self.camp.year, booked_at)

    def early_bird_discount_missed(self):
        """
        Returns the discount that was missed due to failing to book early.
        """
        if self.early_bird_discount or self.price_type == PriceType.CUSTOM:
            return Decimal(0)  # Got the discount, or it wasn't available.
        return Price.objects.get(price_type=PriceType.EARLY_BIRD_DISCOUNT, year=self.camp.year).price

    def age_on_camp(self):
        return relativedelta(self.age_base_date(), self.birth_date).years

    def age_base_date(self):
        # Age is calculated based on school years, i.e. age on 31st August
        # See also PreserveAgeOnCamp.build_update_dict()
        return date(self.camp.year, 8, 31)

    def is_too_young(self):
        return self.age_on_camp() < self.camp.minimum_age

    def is_too_old(self):
        return self.age_on_camp() > self.camp.maximum_age

    def calculate_approvals_needed(self) -> list[ApprovalNeeded]:
        def approval_needed(type: ANT, description: str):
            return ApprovalNeeded(type=type, description=description, booking=self)

        approvals_needed: list[ApprovalNeeded] = []
        if self.serious_illness:
            approvals_needed.append(
                approval_needed(ANT.SERIOUS_ILLNESS, "Must be approved by leader due to serious illness/condition")
            )
        if self.is_custom_discount():
            approvals_needed.append(
                approval_needed(ANT.CUSTOM_PRICE, "A custom discount needs to be arranged by the booking secretary")
            )

        if self.is_too_young() or self.is_too_old():
            camper_age = self.age_on_camp()
            age_base = self.age_base_date().strftime("%e %B %Y")
            camp: Camp = self.camp

            if self.is_too_young():
                approvals_needed.append(
                    approval_needed(
                        ANT.TOO_YOUNG,
                        f"Camper will be {camper_age} which is below the minimum age ({camp.minimum_age}) on {age_base}",
                    )
                )
            elif self.is_too_old():
                approvals_needed.append(
                    approval_needed(
                        ANT.TOO_OLD,
                        f"Camper will be {camper_age} which is above the maximum age ({camp.maximum_age}) on {age_base}",
                    )
                )
        return approvals_needed

    def update_approvals(self) -> None:
        """
        Updates the related BookingApproval objects
        """
        currently_needed = self.calculate_approvals_needed()
        existing: dict[ANT, BookingApproval] = {app.type: app for app in self.approvals.all()}

        to_create: list[BookingApproval] = []
        to_update: list[BookingApproval] = []

        # For each currently needed one, we need to ensure the record exists, and
        # is current.
        for app_needed in currently_needed:
            if (existing_app := existing.pop(app_needed.type, None)) is not None:
                if not existing_app.is_current:
                    existing_app.is_current = True
                    to_update.append(existing_app)
            else:
                to_create.append(app_needed.to_booking_approval())

        # Remaining ones are not current and should be updated.
        for existing_app in existing.values():
            existing_app.is_current = False
            to_update.append(existing_app)

        if to_update:
            BookingApproval.objects.bulk_update(to_update, ["is_current"])
        if to_create:
            BookingApproval.objects.bulk_create(to_create)
        self._clear_approvals_cache()

    @cached_property
    def _cached_approvals(self) -> list[BookingApproval]:
        # This should be pre-populated using with_approvals()
        approvals = list(self.approvals.all())
        approvals.sort(key=lambda app: app.type)
        return approvals

    @property
    def saved_current_approvals(self) -> list[BookingApproval]:
        return [app for app in self._cached_approvals if app.is_current]

    @property
    def saved_approvals_unapproved(self) -> list[BookingApproval]:
        return [app for app in self.saved_current_approvals if not app.is_approved]

    @property
    def saved_approvals_needed_summary(self) -> str:
        return ", ".join(r.short_description for r in self.saved_approvals_unapproved)

    def approve_booking_for_problem(self, type: ApprovalNeededType, user: User) -> None:
        self.approvals.filter(type=type).update(approved_at=timezone.now(), approved_by=user)
        self._clear_approvals_cache()

    def _clear_approvals_cache(self):
        with contextlib.suppress(AttributeError):
            del self._cached_approvals
        with contextlib.suppress(AttributeError):
            self._prefetched_objects_cache.pop("approvals", None)

    def get_available_discounts(self, now):
        retval = []
        if self.can_have_early_bird_discount(booked_at=now):
            discount_amount = Price.objects.get(year=self.camp.year, price_type=PriceType.EARLY_BIRD_DISCOUNT).price
            if discount_amount > 0:
                retval.append(("Early bird discount if booked now", discount_amount))
        return retval

    def get_booking_problems(self, booking_sec=False, agreement_fetcher=None) -> list[BookingProblem]:
        """
        Returns a list of errors and warnings as BookingProblem objects

        If any of these has `blocker == True`, the place cannot be booked by the user.

        If booking_sec=True, it shows the problems as they should be seen by the
        booking secretary.
        """
        # TODO #56 NEXT - rework this so that we don't have a single `APPROVED` state,
        # but each fixable problem can be manually approved.
        #
        # - saving a Booking could create a `BookingApproval`
        #   - migration - create past records?
        # - loading should include them in bulk
        # - on the booking page we should status

        # TODO #56 - instead of this, we need to be able to take into account
        # saved approvals if this Booking has been saved to DB.
        # If it hasn't been saved, we shouldn't do database work, because
        # this code is used sometimes when it hasn't been saved.
        if self.state == BookingState.APPROVED and not booking_sec:
            return []

        return list(self.get_booking_errors(booking_sec=booking_sec, agreement_fetcher=agreement_fetcher)) + list(
            self.get_booking_warnings(booking_sec=booking_sec)
        )

    def get_booking_errors(self, booking_sec=False, agreement_fetcher=None) -> Sequence[BookingProblem]:
        errors: list[ApprovalNeeded | Blocker] = []
        camp: Camp = self.camp

        def blocker(description: str) -> Blocker:
            return Blocker(description=description)

        errors.extend(self.calculate_approvals_needed())

        relevant_bookings = self.account.bookings.for_year(camp.year).in_basket_or_booked()
        relevant_bookings_excluding_self = relevant_bookings.exclude(
            first_name=self.first_name, last_name=self.last_name
        )
        relevant_bookings_limited_to_self = relevant_bookings.filter(
            first_name=self.first_name, last_name=self.last_name
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

        if self.price_type == PriceType.SECOND_CHILD:
            if not (relevant_bookings_excluding_self.filter(price_type=PriceType.FULL)).exists():
                errors.append(
                    blocker(
                        "You cannot use a 2nd child discount unless you have "
                        "another child at full price. Please edit the place details "
                        "and choose an appropriate price type."
                    )
                )

        if self.price_type == PriceType.THIRD_CHILD:
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

        if self.price_type in [PriceType.SECOND_CHILD, PriceType.THIRD_CHILD]:
            qs = relevant_bookings_limited_to_self
            qs = qs.filter(price_type=PriceType.SECOND_CHILD) | qs.filter(price_type=PriceType.THIRD_CHILD)
            if qs.count() > 1:
                errors.append(
                    blocker("If a camper goes on multiple camps, only one place may use a 2nd/3rd child discount.")
                )

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
                You can <a href="{1}" target="_new">contact the booking secretary</a>
                to be put on a waiting list. """,
                msg,
                reverse("cciw-contact_us-send") + "?bookings",
            )

        # Simple - no places left
        if places_left.total <= 0:
            errors.append(blocker(no_places_available_message("There are no places left on this camp.")))
            places_available = False

        SEXES = [
            (Sex.MALE, "boys", places_left.male),
            (Sex.FEMALE, "girls", places_left.female),
        ]

        if places_available:
            for sex_const, sex_label, places_left_for_sex in SEXES:
                if self.sex == sex_const and places_left_for_sex <= 0:
                    errors.append(
                        blocker(no_places_available_message(f"There are no places left for {sex_label} on this camp."))
                    )
                    places_available = False
                    break

        if places_available:
            # Complex - need to check the other places that are about to be booked.
            # (if there is one place left, and two campers for it, we can't say that
            # there are enough places)
            same_camp_bookings = self.account.bookings.filter(camp=camp).in_basket()
            places_to_be_booked = len(same_camp_bookings)

            if places_left.total < places_to_be_booked:
                errors.append(
                    blocker(
                        no_places_available_message(
                            "There are not enough places left on this camp for the campers in this set of bookings."
                        )
                    )
                )
                places_available = False

            if places_available:
                for sex_const, sex_label, places_left_for_sex in SEXES:
                    if self.sex == sex_const:
                        places_to_be_booked_for_sex = len([b for b in same_camp_bookings if b.sex == sex_const])
                        if places_left_for_sex < places_to_be_booked_for_sex:
                            errors.append(
                                blocker(
                                    no_places_available_message(
                                        f"There are not enough places for {sex_label} left on this camp "
                                        "for the campers in this set of bookings."
                                    )
                                )
                            )
                            places_available = False
                            break

        if self.south_wales_transport and not camp.south_wales_transport_available:
            errors.append(
                blocker(
                    "Transport from South Wales is not available for this camp, or all places have been taken already."
                )
            )

        if booking_sec and self.price_type != PriceType.CUSTOM:
            expected_amount = self.expected_amount_due()
            if self.amount_due != expected_amount:
                errors.append(blocker(f"The 'amount due' is not the expected value of £{expected_amount}."))

        if booking_sec and not self.created_online:
            if self.early_bird_discount:
                errors.append(blocker("The early bird discount is only allowed for bookings created online."))

        # Don't want warnings for booking sec when a booked place is edited
        # after the cutoff date, so we allow self.booked_at to be used here:
        on_date: date = self.booked_at if self.is_booked and self.booked_at is not None else date.today()

        if not camp.open_for_bookings(on_date):
            if on_date >= camp.end_date:
                msg = "This camp has already finished."
            elif on_date >= camp.start_date:
                msg = "This camp is closed for bookings because it has already started."
            else:
                msg = "This camp is closed for bookings."
            errors.append(blocker(msg))

        missing_agreements = self.get_missing_agreements(agreement_fetcher=agreement_fetcher)
        for agreement in missing_agreements:
            errors.append(blocker(f'You need to confirm your agreement in section "{agreement.name}"'))

        return errors

    def get_booking_warnings(self, booking_sec=False) -> list[BookingProblem]:
        camp: Camp = self.camp
        warnings: list[str] = []

        if self.account.bookings.filter(first_name=self.first_name, last_name=self.last_name, camp=camp).exclude(
            id=self.id
        ):
            warnings.append(
                f"You have entered another set of place details for a camper "
                f"called '{self.name}' on camp {camp.name}. Please ensure you don't book multiple "
                f"places for the same camper!"
            )

        relevant_bookings = self.account.bookings.for_year(camp.year).in_basket_or_booked()

        if self.price_type == PriceType.FULL:
            full_pricers = relevant_bookings.filter(price_type=PriceType.FULL)
            names = sorted({b.name for b in full_pricers})
            if len(names) > 1:
                pretty_names = ", ".join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at 'Full price'. "
                if len(names) == 2:
                    warning += (
                        f"If {pretty_names} are from the same family, one is eligible for the 2nd child discount."
                    )
                else:
                    warning += f"If {pretty_names} are from the same family, one or more is eligible for the 2nd or 3rd child discounts."

                warnings.append(warning)

        if self.price_type == PriceType.SECOND_CHILD:
            second_childers = relevant_bookings.filter(price_type=PriceType.SECOND_CHILD)
            names = sorted({b.name for b in second_childers})
            if len(names) > 1:
                pretty_names = ", ".join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at '2nd child discount'. "
                if len(names) == 2:
                    warning += (
                        f"If {pretty_names} are from the same family, one is eligible for the 3rd child discount."
                    )
                else:
                    warning += (
                        f"If {pretty_names} are from the same family, {len(names) - 1} are eligible "
                        f"for the 3rd child discount."
                    )

                warnings.append(warning)

        return [Warning(description=warning) for warning in warnings]

    def confirm(self):
        self.booking_expires_at = None
        self.save()

    def expire(self):
        self._unbook()
        self.save()

    def cancel_and_move_to_shelf(self):
        self._unbook()
        self.shelved = True
        self.save()

    def _unbook(self):
        self.booking_expires_at = None
        # Here we don't use BookingState.CANCELLED_FULL_REFUND,
        # because we assume the user might want to edit and book
        # again:
        self.state = BookingState.INFO_COMPLETE
        self.early_bird_discount = False
        self.booked_at = None
        self.auto_set_amount_due()
        self.save()

    def is_user_editable(self):
        return self.state == BookingState.INFO_COMPLETE or self.state == BookingState.BOOKED and self.missing_agreements

    def is_custom_discount(self):
        return self.price_type == PriceType.CUSTOM

    @cached_property
    def missing_agreements(self):
        return self.get_missing_agreements()

    def get_missing_agreements(self, *, agreement_fetcher=None):
        if agreement_fetcher is None:
            agreement_fetcher = AgreementFetcher()
        return [
            agreement
            for agreement in agreement_fetcher.fetch(year=self.camp.year)
            if agreement.id not in self.custom_agreements_checked
        ]

    def get_contact_email(self):
        if self.email:
            return self.email
        elif self.account_id is not None:
            return self.account.email

    def get_address_display(self):
        return "\n".join(
            v
            for v in [
                self.address_line1,
                self.address_line2,
                self.address_city,
                self.address_county,
                self.address_country.code if self.address_country else None,
                self.address_post_code,
            ]
            if v
        )

    def get_contact_address_display(self):
        return "\n".join(
            v
            for v in [
                self.contact_name,
                self.contact_line1,
                self.contact_line2,
                self.contact_city,
                self.contact_county,
                self.contact_country.code if self.contact_country else None,
                self.contact_post_code,
            ]
            if v
        )

    def get_gp_address_display(self):
        return "\n".join(
            v
            for v in [
                self.gp_line1,
                self.gp_line2,
                self.gp_city,
                self.gp_county,
                self.gp_country.code if self.gp_country else None,
                self.gp_post_code,
            ]
            if v
        )


# Attributes that the account holder is allowed to see
BOOKING_PLACE_USER_VISIBLE_ATTRS = [
    "id",
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "address_line1",
    "address_line2",
    "address_city",
    "address_county",
    "address_country",
    "address_post_code",
    "phone_number",
    "church",
    "contact_name",
    "contact_line1",
    "contact_line2",
    "contact_city",
    "contact_county",
    "contact_country",
    "contact_post_code",
    "contact_phone_number",
    "dietary_requirements",
    "gp_name",
    "gp_line1",
    "gp_line2",
    "gp_city",
    "gp_county",
    "gp_country",
    "gp_post_code",
    "gp_phone_number",
    "medical_card_number",
    "last_tetanus_injection_date",
    "allergies",
    "regular_medication_required",
    "learning_difficulties",
    "serious_illness",
    "created_at",
]

# BookingAccount fields we can copy to Booking for camper address
BOOKING_ACCOUNT_ADDRESS_TO_CAMPER_ADDRESS_FIELDS = {
    "address_line1": "address_line1",
    "address_line2": "address_line2",
    "address_city": "address_city",
    "address_county": "address_county",
    "address_country": "address_country",
    "address_post_code": "address_post_code",
    "phone_number": "phone_number",
}

# BookingAccount fields we can copy to Booking for contact address
BOOKING_ACCOUNT_ADDRESS_TO_CONTACT_ADDRESS_FIELDS = {
    "name": "contact_name",
    "address_line1": "contact_line1",
    "address_line2": "contact_line2",
    "address_city": "contact_city",
    "address_county": "contact_county",
    "address_country": "contact_country",
    "address_post_code": "contact_post_code",
    "phone_number": "contact_phone_number",
}

# Booking fields that can be copied from previous Bookings:
BOOKING_PLACE_CAMPER_DETAILS = [
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "church",
    "dietary_requirements",
    "medical_card_number",
    "last_tetanus_injection_date",
    "allergies",
    "regular_medication_required",
    "illnesses",
    "can_swim_25m",
    "learning_difficulties",
    "serious_illness",
]
BOOKING_PLACE_CAMPER_ADDRESS_DETAILS = [
    "address_line1",
    "address_line2",
    "address_city",
    "address_county",
    "address_country",
    "address_post_code",
    "phone_number",
]
BOOKING_PLACE_CONTACT_ADDRESS_DETAILS = [
    "contact_name",
    "contact_line1",
    "contact_line2",
    "contact_city",
    "contact_county",
    "contact_country",
    "contact_post_code",
    "contact_phone_number",
]
BOOKING_PLACE_GP_DETAILS = [
    "gp_name",
    "gp_line1",
    "gp_line2",
    "gp_city",
    "gp_county",
    "gp_country",
    "gp_post_code",
    "gp_phone_number",
]
