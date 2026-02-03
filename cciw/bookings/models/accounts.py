from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Q, functions
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django_countries.fields import CountryField
from paypal.standard.ipn.models import PayPalIPN

from .constants import DEFAULT_COUNTRY
from .states import BOOKING_STATES_NO_FEE_DUE
from .yearconfig import YearConfigFetcher

if TYPE_CHECKING:
    from .bookings import Booking


class BookingAccountQuerySet(models.QuerySet):
    def not_in_use(self, now: datetime) -> BookingAccountQuerySet:
        from .bookings import Booking

        return self.zero_final_balance().exclude(
            id__in=Booking.objects.in_use(now).values_list("account_id", flat=True)
        )

    def older_than(self, before_datetime: datetime) -> BookingAccountQuerySet:
        """
        Returns BookingAccounts that are considered 'older than' before_datetime
        in terms of when they were last 'used'
        """
        return (
            self.filter(
                # last_login_at/created_at
                models.ExpressionWrapper(
                    RawSQL(
                        """
              (CASE WHEN bookings_bookingaccount.last_login_at IS NOT NULL THEN bookings_bookingaccount.last_login_at
                    ELSE bookings_bookingaccount.created_at
               END) < %s
              """,
                        [before_datetime],
                    ),
                    output_field=models.BooleanField(),
                )
            )
            .alias(
                # payments
                last_payment_at=models.Max("payments__created_at"),
            )
            .filter(Q(last_payment_at__isnull=True) | Q(last_payment_at__lt=before_datetime))
            .alias(
                # bookings
                last_booking_camp_end_date=models.Max("bookings__camp__end_date"),
            )
            .filter(Q(last_booking_camp_end_date__isnull=True) | Q(last_booking_camp_end_date__lt=before_datetime))
        )

    def _with_total_amount_due(self) -> BookingAccountQuerySet:
        return self.alias(
            total_amount_due=functions.Coalesce(
                models.Sum(
                    "bookings__amount_due",
                    filter=~Q(bookings__state__in=BOOKING_STATES_NO_FEE_DUE),
                ),
                models.Value(Decimal(0)),
            )
        )

    def zero_final_balance(self) -> BookingAccountQuerySet:
        # See also below
        return self._with_total_amount_due().filter(total_amount_due=models.F("total_received"))

    def non_zero_final_balance(self) -> BookingAccountQuerySet:
        # See also above
        return self._with_total_amount_due().exclude(total_amount_due=models.F("total_received"))


class BookingAccountManagerBase(models.Manager):
    def payments_due(self) -> Sequence[BookingAccount]:
        """
        Returns a list of accounts that owe money.
        Account objects are annotated with attribute 'confirmed_balance_due' as a Decimal
        """
        # To limit the size of queries, we do a SQL query for people who might
        # owe money.
        potentials: Sequence[BookingAccount] = self.get_queryset().non_zero_final_balance()
        # 'balance due now' can be less than 'final balance', because we
        # allow bookings without payment before a certain date
        retval: list[BookingAccount] = []
        account: BookingAccount
        today = date.today()

        # TODO - we could probably make this more efficient, perhaps
        # combine some logic with outstanding_bookings_with_fees()?

        config_fetcher = YearConfigFetcher()
        for account in potentials:
            confirmed_balance_due = account.get_balance(today=today, config_fetcher=config_fetcher)
            if confirmed_balance_due > 0:
                account.confirmed_balance_due = confirmed_balance_due
                retval.append(account)
        return retval


BookingAccountManager = BookingAccountManagerBase.from_queryset(BookingAccountQuerySet)


# Public attributes - i.e. that the account holder is allowed to see
ACCOUNT_PUBLIC_ATTRS = [
    "email",
    "name",
    "address_line1",
    "address_line2",
    "address_city",
    "address_county",
    "address_country",
    "address_post_code",
    "phone_number",
]


class BookingAccount(models.Model):
    """
    Login account for camp bookings system.
    """

    # For online bookings, email is required, but not for paper. Initially for online
    # process only email is filled in, so to ensure we can edit all BookingAccounts
    # in the admin, all the address fields have 'blank=True'.
    # We have email with null=True so that we can have unique=True on that field.
    email = models.EmailField(blank=True, unique=True, null=True)
    name = models.CharField(blank=True, max_length=100)
    address_line1 = models.CharField("address line 1", max_length=255, blank=True)
    address_line2 = models.CharField("address line 2", max_length=255, blank=True)
    address_city = models.CharField("town/city", max_length=255, blank=True)
    address_county = models.CharField("county/state", max_length=255, blank=True)
    address_country = CountryField("country", null=True, blank=True, default=DEFAULT_COUNTRY)
    address_post_code = models.CharField("post code", blank=True, max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    share_phone_number = models.BooleanField(
        "Allow this phone number to be passed on to other parents to help organise transport",
        blank=True,
        default=False,
    )
    email_communication = models.BooleanField(
        "Receive all communication from CCiW by email where possible", blank=True, default=True
    )
    subscribe_to_mailings = models.BooleanField(
        "Receive mailings about future camps", default=None, blank=True, null=True
    )
    subscribe_to_newsletter = models.BooleanField("Subscribe to email newsletter", default=False)
    total_received = models.DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=10)
    created_at = models.DateTimeField(blank=False)
    first_login_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_payment_reminder_at = models.DateTimeField(null=True, blank=True)

    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = BookingAccountManager()

    def has_account_details(self) -> bool:
        return not any(
            att == ""
            for att in [self.name, self.address_line1, self.address_city, self.address_country, self.address_post_code]
        )

    def __str__(self) -> str:
        out = []
        if self.name:
            out.append(self.name)
        if self.address_post_code:
            out.append(self.address_post_code)
        if self.email:
            out.append("<" + self.email + ">")
        if not out:
            out.append("(empty)")
        return ", ".join(out)

    def save(self, **kwargs) -> None:
        # We have to ensure that only receive_payment touches the total_received
        # field when doing updates
        if self.id is None:
            self.created_at = timezone.now()
            return super().save(**kwargs)
        else:
            update_fields = [f.name for f in self._meta.fields if f.name != "id" and f.name != "total_received"]
            return super().save(update_fields=update_fields, **kwargs)

    # Business methods:

    def get_balance(self, *, today: date | None, config_fetcher: YearConfigFetcher | None = None) -> Decimal:
        """
        Gets the balance to pay on the account.
        If today is None, then the final balance is returned,
        not the amount currently due.
        """
        # Use of _prefetched_objects_cache is necessary to support the
        # booking_secretary_reports view efficiently
        if hasattr(self, "_prefetched_objects_cache") and "bookings" in self._prefetched_objects_cache:
            payable_bookings = [
                booking for booking in self._prefetched_objects_cache["bookings"] if booking.is_payable()
            ]
        else:
            payable_bookings = list(self.bookings.payable())

        total = Decimal("0.00")
        if config_fetcher is None:
            config_fetcher = YearConfigFetcher()

        booking: Booking
        for booking in payable_bookings:
            total += booking.get_amount_due(today=today, config_fetcher=config_fetcher)

        return total - self.total_received

    def get_balance_full(self) -> Decimal:
        return self.get_balance(today=None)

    def get_balance_due_now(self) -> Decimal:
        today = date.today()
        return self.get_balance(today=today)

    def admin_balance(self) -> Decimal:
        return self.get_balance_full()

    admin_balance.short_description = "balance"
    admin_balance = property(admin_balance)

    def receive_payment(self, amount: Decimal):
        """
        Adds the amount to the account's total_received field.  This should only
        ever be called by the 'process_all_payments' function. Client code
        should use the 'send_payment' function.
        """
        # See process_all_payments function for an explanation of the above

        # = Receiving payments =
        #
        # When an online payment is received, django-paypal creates a record
        # and a signal handler indirectly calls this method which must update
        # the 'total_received' field.
        #
        # The manual booking process, which uses the admin to record cheque
        # payments, uses exactly the same process, although it is a different
        # payment object which triggers the process.

        # Use update and F objects to avoid concurrency problems
        BookingAccount.objects.filter(id=self.id).update(total_received=models.F("total_received") + amount)

        # Need new data from DB:
        acc = BookingAccount.objects.get(id=self.id)
        self.total_received = acc.total_received

    def get_pending_payment_total(self, now: datetime | None = None) -> Decimal:
        from .payments import build_paypal_custom_field

        if now is None:
            now = timezone.now()

        custom = build_paypal_custom_field(self)
        all_payments = PayPalIPN.objects.filter(
            custom=custom,
        )
        pending_payments = all_payments.filter(
            payment_status="Pending",
            payment_date__gt=now - timedelta(days=3 * 30),  # old ones don't count
        )
        completed_payments = all_payments.filter(
            payment_status="Completed",
        )
        uncompleted_pending_payments = pending_payments.exclude(txn_id__in=[ipn.txn_id for ipn in completed_payments])

        total = uncompleted_pending_payments.aggregate(total=models.Sum("mc_gross"))["total"]
        if total is None:
            return Decimal("0.00")
        return total

    def get_address_display(self) -> str:
        return "\n".join(
            v
            for v in [
                self.address_line1,
                self.address_line2,
                self.address_city,
                self.address_county,
                self.address_country.code if self.address_country else None,
            ]
            if v
        )

    @property
    def include_in_mailings(self) -> bool:
        if self.subscribe_to_mailings is None:
            # GDPR. We have not obtained an answer to this question.
            # For postal mailings, by legitimate interest we
            # are allowed to assume 'Yes'
            return True
        else:
            return self.subscribe_to_mailings
