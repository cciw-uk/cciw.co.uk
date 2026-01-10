from __future__ import annotations

import contextlib
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, QuerySet, Value, functions
from django.utils import timezone
from django.utils.functional import cached_property
from django_countries.fields import CountryField

from cciw.accounts.models import User
from cciw.bookings.models.queue import BookingQueueEntry
from cciw.cciwmain.models import Camp
from cciw.utils.models import AfterFetchQuerySetMixin

from .accounts import BookingAccount
from .agreements import AgreementFetcher, CustomAgreement
from .constants import DEFAULT_COUNTRY, Sex
from .prices import BOOKING_PLACE_PRICE_TYPES, Price, PriceType
from .problems import (
    ApprovalNeededType,
    ApprovalStatus,
    BookingApproval,
    BookingProblem,
    calculate_approvals_needed,
    get_booking_problems,
)
from .states import BookingState
from .utils import sql_normalise_booking_name
from .yearconfig import YearConfigFetcher, early_bird_is_available

if TYPE_CHECKING:
    from .problems import BookingApproval

ANT = ApprovalNeededType


class Array(models.Func):
    function = "ARRAY"


class BookingQuerySet(AfterFetchQuerySetMixin, models.QuerySet):
    def for_year(self, year: int) -> BookingQuerySet:
        return self.filter(camp__year__exact=year)

    def for_camp(self, camp: Camp) -> BookingQuerySet:
        return self.filter(camp=camp)

    def in_basket(self) -> BookingQuerySet:
        return self.filter(shelved=False, state=BookingState.INFO_COMPLETE)

    def on_shelf(self) -> BookingQuerySet:
        return self.filter(shelved=True, state=BookingState.INFO_COMPLETE)

    def booked(self) -> BookingQuerySet:
        return self.filter(state=BookingState.BOOKED)

    def basket_relevant(self) -> BookingQuerySet:
        """
        Returns bookings that are relevant to "basket" stage in which
        problems that span bookings need to be found.
        """
        # This includes things that are already booked,
        # or are about to be booked.
        return self.in_basket() | self.booked()

    def in_queue(self) -> BookingQuerySet:
        return self.filter(queue_entry__isnull=False, queue_entry__is_active=True)

    def not_in_queue(self) -> BookingQuerySet:
        return self.filter(queue_entry__isnull=True) | self.filter(queue_entry__is_active=False)

    def waiting_in_queue(self) -> BookingQuerySet:
        return self.in_queue().filter(state=BookingState.INFO_COMPLETE)

    def accepted_in_queue(self) -> BookingQuerySet:
        return self.in_queue().filter(state=BookingState.BOOKED)

    def payable(self) -> BookingQuerySet:
        """
        Returns bookings for which payment is expected.
        """
        # See also:
        #   Booking.is_payable()

        # Also booking_secretary_reports has overlapping logic.

        # 'Full refund' cancelled bookings do not have payment expected, but the
        # others do.
        return (
            self.filter(state__in=[BookingState.CANCELLED_DEPOSIT_KEPT, BookingState.CANCELLED_HALF_REFUND])
            | self.booked()
        )

    def cancelled(self) -> BookingQuerySet:
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
        qs = self.filter(state=BookingState.INFO_COMPLETE).in_basket().select_related("camp")
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

    def with_queue_info(self) -> BookingQuerySet:
        return self.select_related("queue_entry")

    # Data retention

    def not_in_use(self, now: datetime):
        return self.exclude(self._in_use_q(now))

    def in_use(self, now: datetime):
        return self.filter(self._in_use_q(now))

    def _in_use_q(self, now: datetime):
        # See also BookingQueueEntryQuerySet.not_in_use()
        return Q(
            camp__end_date__gte=now.date(),
        )

    def older_than(self, before_datetime: datetime):
        # See also BookingQueueEntryQuerySet.older_than()
        return self.filter(created_at__lt=before_datetime, camp__end_date__lt=before_datetime)

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
    price_type = models.CharField(choices=[(pt, pt.label) for pt in BOOKING_PLACE_PRICE_TYPES])
    early_bird_discount = models.BooleanField(default=False, help_text="Online bookings only")
    booked_at = models.DateTimeField(null=True, blank=True, help_text="Online bookings only")
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - user driven
    shelved = models.BooleanField(default=False, help_text="Used by user to put on 'shelf'")

    # State - internal
    state = models.CharField(choices=BookingState)

    created_at = models.DateTimeField(default=timezone.now)
    created_online = models.BooleanField(blank=True, default=False)

    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    # Generated:

    # fuzzy_camper_id is used for matching campers from one year to the next.
    # Unfortunately it isn't easy to do this precisely, as we don't have a
    # proper concept of "camper identity".
    #
    # We use "full name plus birth year" as an approximate solution. For our
    # scale of data, this works well:
    # - we do have some duplicate names, so birth year is necessary
    # - we can't use full birth_date, because:
    #   - about 2% of people make mistakes and correct in subsequent years
    #   - our GDPR scrubbing removes exact birth date (while leaving birth year)

    fuzzy_camper_id = models.GeneratedField(
        expression=functions.Concat(
            sql_normalise_booking_name(),
            Value(" "),
            functions.Cast(functions.ExtractYear("birth_date"), output_field=models.CharField()),
        ),
        output_field=models.CharField(),
        db_persist=True,
        db_index=True,
    )

    # fuzzy_camper_id_strict is a narrower version of the above,
    # that also limits to same booking account. This is far less likely
    # to result in false positives when matching.
    fuzzy_camper_id_strict = models.GeneratedField(
        expression=functions.Concat(
            functions.Cast("account_id", output_field=models.CharField()),
            Value(" "),
            sql_normalise_booking_name(),
            functions.Cast(functions.ExtractYear("birth_date"), output_field=models.CharField()),
        ),
        output_field=models.CharField(),
        db_persist=True,
        db_index=True,
    )

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

    def is_payable(self) -> bool:
        # See also BookingQuerySet.payable()
        return self.state in [BookingState.CANCELLED_DEPOSIT_KEPT, BookingState.CANCELLED_HALF_REFUND] or self.is_booked

    @property
    def is_booked(self) -> bool:
        return self.state == BookingState.BOOKED

    @property
    def _queue_entry_or_none(self) -> BookingQueueEntry | None:
        try:
            return self.queue_entry
        except BookingQueueEntry.DoesNotExist:
            return None

    @property
    def is_in_queue(self) -> bool:
        return (queue_entry := self._queue_entry_or_none) is not None and queue_entry.is_active

    def add_to_queue(self) -> BookingQueueEntry:
        queue_entry = self._queue_entry_or_none
        if queue_entry is not None:
            if not queue_entry.is_active:
                queue_entry.make_active()
        else:
            queue_entry = BookingQueueEntry.objects.create_for_booking(self)
            self.queue_entry = queue_entry
        return queue_entry

    def withdraw_from_queue(self) -> None:
        if self.is_in_queue:
            self.queue_entry.make_inactive()

    def expected_amount_due(self) -> Decimal | None:
        if self.price_type == PriceType.CUSTOM:
            return None
        if self.state == BookingState.CANCELLED_DEPOSIT_KEPT:
            try:
                return Price.objects.get(year=self.camp.year, price_type=PriceType.DEPOSIT).price
            except Price.DoesNotExist:
                # No deposit, assume same as CANCELLED_FULL_REFUND
                return Decimal("0.00")
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
        if self.camp.year < 2026:
            # Business rules have changed, we can't calculate expected amount due
            # any more, and we shouldn't every need to do this for old bookings.
            return
        amount = self.expected_amount_due()
        if amount is None:
            # This happens for PriceType.CUSTOM
            if self.amount_due is None:
                self.amount_due = Decimal("0.00")
            # Otherwise - should leave as it was.
        else:
            self.amount_due = amount

    @property
    def amount_due_confirmed(self) -> None | Decimal:
        # Where booking.price_type == PriceType.CUSTOM, and state is not approved,
        # amount_due is zero, but this is meaningless.
        # So we have this attribute that only returns a value if the amount is approved.
        if self.price_type == PriceType.CUSTOM and not self.custom_price_is_approved:
            return None
        return self.amount_due

    def get_amount_due(self, *, today: date | None, config_fetcher: YearConfigFetcher) -> Decimal:
        """
        Get the amount due,
        if `today` is None, return the final amount due,
        otherwise the amount due right now.
        """
        full_amount: Decimal = self.amount_due
        if today is not None:
            # If we have a YearConfig (which will be true for any bookings from
            # 2026 onwards), we can use the `payments_due_on` date.

            # If we don't (for all earlier bookings), we can assume the booking
            # is past and payment is due.

            # To avoid doing unnecessary lookups, we can also assume that for any
            # booking where the camp is past, the payment is due.
            if self.camp.end_date < today:
                return full_amount

            year_config = config_fetcher.lookup_year(self.camp.year)
            if year_config is None:
                # No info‚ assume past
                return full_amount

            if today < year_config.payments_due_on:
                return Decimal(0)
            else:
                return full_amount

        return full_amount

    def can_have_early_bird_discount(self, booked_at=None):
        if booked_at is None:
            booked_at = self.booked_at
        if self.price_type == PriceType.CUSTOM:
            return False
        else:
            return early_bird_is_available(year=self.camp.year, booked_at=booked_at)

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

    def update_approvals(self) -> None:
        """
        Updates the related BookingApproval objects
        """
        currently_needed = calculate_approvals_needed(self)
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

    @cached_property
    def saved_current_approvals_dict(self) -> dict[ANT, BookingApproval]:
        return {ANT(app.type): app for app in self.saved_current_approvals}

    @property
    def saved_approvals_unapproved(self) -> list[BookingApproval]:
        return [app for app in self.saved_current_approvals if not app.is_approved]

    @property
    def saved_approvals_needed_summary(self) -> str:
        return ", ".join(r.short_description for r in self.saved_approvals_unapproved)

    @property
    def custom_price_is_approved(self) -> bool:
        try:
            return self.saved_current_approvals_dict[ANT.CUSTOM_PRICE].is_approved
        except KeyError:
            return False

    def approve_booking_for_problem(self, type: ApprovalNeededType, user: User) -> None:
        # MAYBE we don't need this method, it is only used by tests, approvals
        # are done in admin and work differently
        self.approvals.filter(type=type).update(
            status=ApprovalStatus.APPROVED, checked_at=timezone.now(), checked_by=user
        )
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
        return get_booking_problems(self, booking_sec=booking_sec, agreement_fetcher=agreement_fetcher)

    def confirm(self):
        # TODO #52 - should involve queue?
        self.state = BookingState.BOOKED
        self.save()

    def cancel_and_move_to_shelf(self):
        self._unbook()
        self.shelved = True
        self.save()

    def _unbook(self):
        # TODO #52 - change entry on the queue?

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
