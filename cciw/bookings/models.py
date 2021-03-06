# -*- coding: utf-8 -*-
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from paypal.standard.ipn.models import PayPalIPN

from cciw.bookings.email import send_booking_expiry_mail
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp

from .signals import places_confirmed

# = Business rules =
#
# Business rules are implemented in relevant models and managers.
#
# Some business logic duplicated in
# cciw.officers.views.booking_secretary_reports for performance reasons.


class Sex(models.TextChoices):
    MALE = 'm', 'Male'
    FEMALE = 'f', 'Female'


# Price types that can be selected in a booking or appear in Prices table.
class PriceType(models.IntegerChoices):
    FULL = 0, 'Full price'
    SECOND_CHILD = 1, '2nd child discount'
    THIRD_CHILD = 2, '3rd child discount'
    CUSTOM = 3, 'Custom discount'
    SOUTH_WALES_TRANSPORT = 4, 'South wales transport surcharge (pre 2015)'
    DEPOSIT = 5, 'Deposit'
    EARLY_BIRD_DISCOUNT = 6, 'Early bird discount'


BOOKING_PLACE_PRICE_TYPES = [PriceType.FULL, PriceType.SECOND_CHILD, PriceType.THIRD_CHILD, PriceType.CUSTOM]

# Price types that are used by Price model
VALUED_PRICE_TYPES = (
    [val for val in BOOKING_PLACE_PRICE_TYPES if val != PriceType.CUSTOM] +
    [PriceType.SOUTH_WALES_TRANSPORT, PriceType.DEPOSIT, PriceType.EARLY_BIRD_DISCOUNT]
)


# Prices required to open bookings.
# From 2015 onwards, we don't have South Wales transport. But we might
# want to keep info about prices etc. for a few years.
REQUIRED_PRICE_TYPES = [v for v in VALUED_PRICE_TYPES if v != PriceType.SOUTH_WALES_TRANSPORT]


class BookingState(models.IntegerChoices):
    INFO_COMPLETE = 0, 'Information complete'
    APPROVED = 1, 'Manually approved'
    BOOKED = 2, 'Booked'
    CANCELLED_DEPOSIT_KEPT = 3, 'Cancelled - deposit kept'
    CANCELLED_HALF_REFUND = 4, 'Cancelled - half refund (pre 2015 only)'
    CANCELLED_FULL_REFUND = 5, 'Cancelled - full refund'


class ManualPaymentType(models.IntegerChoices):
    CHEQUE = 0, 'Cheque'
    CASH = 1, 'Cash'
    ECHEQUE = 2, 'e-Cheque'
    BACS = 3, 'Bank transfer'


class NoEditMixin(object):
    def clean(self):
        retval = super(NoEditMixin, self).clean()
        if self.id is not None:
            raise ValidationError("A {0} record cannot be changed "
                                  "after being created. If an error was made, "
                                  "delete this record and create a new one. "
                                  .format(self.__class__._meta.verbose_name))
        return retval

    def save(self, **kwargs):
        if self.id is not None:
            raise Exception("%s cannot be edited after it has been saved to DB" %
                            self.__class__.__name__)
        else:
            return super(NoEditMixin, self).save(**kwargs)


class PriceQuerySet(models.QuerySet):

    def required_for_booking(self):
        return self.filter(price_type__in=REQUIRED_PRICE_TYPES)


class Price(models.Model):
    year = models.PositiveSmallIntegerField()
    price_type = models.PositiveSmallIntegerField(choices=[(pt, pt.label) for pt in VALUED_PRICE_TYPES])
    price = models.DecimalField(decimal_places=2, max_digits=10)

    objects = models.Manager.from_queryset(PriceQuerySet)()

    class Meta:
        unique_together = [('year', 'price_type')]

    def __str__(self):
        return f"{self.get_price_type_display()} {self.year} - {self.price}"

    @classmethod
    def get_deposit_prices(cls, years=None):
        q = Price.objects.filter(price_type=PriceType.DEPOSIT)
        if years is not None:
            q = q.filter(year__in=set(years))
        return {p.year: p.price for p in q}


class PriceChecker:
    """
    Utility that looks up prices, with caching to reduce queries
    """
    # We don't look up prices immediately, but lazily, because there are
    # quite a few paths that don't need the deposit price at all,
    # and they can happen in a loop e.g. BookingAccount.get_balance_full()
    def __init__(self, expected_years=None):
        self._deposit_prices = {}
        self._expected_years = expected_years or []

    def _fetch_deposit_prices(self, year):
        if year in self._deposit_prices:
            return
        # Try to get everything we think we'll need in a single query,
        # and cache for later.
        years = set(self._expected_years + [year])
        prices = Price.objects.filter(price_type=PriceType.DEPOSIT).filter(year__in=years)
        self._deposit_prices.update({p.year: p.price for p in prices})

    def get_deposit_price(self, year):
        self._fetch_deposit_prices(year)
        return self._deposit_prices[year]


class BookingAccountQuerySet(models.QuerySet):
    pass


class BookingAccountManagerBase(models.Manager):
    def payments_due(self):
        """
        Returns a list of accounts that owe money.
        Account objects are annotated with attribute 'confirmed_balance_due' as a Decimal
        """
        # To limit the size of queries, we do a SQL query for people who might
        # owe money.
        potentials = (
            self.get_queryset()
            .annotate(total_amount_due=models.Sum('bookings__amount_due'))
            .exclude(total_amount_due=models.F('total_received'))
        )
        retval = []
        price_checker = PriceChecker()
        for account in potentials:
            confirmed_balance_due = account.get_balance(
                confirmed_only=True,
                allow_deposits=True,
                price_checker=price_checker,
            )
            if confirmed_balance_due > 0:
                account.confirmed_balance_due = confirmed_balance_due
                retval.append(account)
        return retval


BookingAccountManager = BookingAccountManagerBase.from_queryset(BookingAccountQuerySet)


MAILCHIMP_NOTICE = mark_safe("""<span class='mailchimp-notice'>We use a third party email service provider,
MailChimp, to send you these newsletter emails. We provide MailChimp with only
your email address. MailChimp treats information about you in accordance with
the provisions of its <a href='https://mailchimp.com/legal/privacy/'>Privacy
Policy</a>. MailChimp also utilizes certain technologies, such as pixels and web
beacons, in the emails that are sent through MailChimp. These technologies allow
MailChimp to track whether you have opened or clicked on our emails and if so,
the date, time, and IP address associated with the open and/or click. For more
information on MailChimp's use of these technologies, you can read their <a
href='https://mailchimp.com/legal/cookies/'>Cookie Statement</a>.</span>""")


class BookingAccount(models.Model):
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
    address_country = CountryField("country", null=True, blank=True)
    address_post_code = models.CharField("post code", blank=True, max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    share_phone_number = models.BooleanField("Allow this phone number to be passed on "
                                             "to other parents to help organise transport",
                                             blank=True, default=False)
    email_communication = models.BooleanField("Receive all communication from CCiW by email where possible", blank=True, default=True)
    subscribe_to_mailings = models.BooleanField("Receive mailings about future camps",
                                                default=None, blank=True, null=True)
    subscribe_to_newsletter = models.BooleanField("Subscribe to email newsletter", default=False,
                                                  help_text=MAILCHIMP_NOTICE)
    total_received = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits=10)
    first_login = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_payment_reminder = models.DateTimeField(null=True, blank=True)

    objects = BookingAccountManager()

    def has_account_details(self):
        return not any(getattr(self, f) == ""
                       for f in ['name',
                                 'address_line1',
                                 'address_city',
                                 'address_country',
                                 'address_post_code'])

    def __str__(self):
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

    def save(self, **kwargs):
        # We have to ensure that only receive_payment touches the total_received
        # field when doing updates
        if self.id is None:
            return super(BookingAccount, self).save(**kwargs)
        else:
            update_fields = [f.name for f in self._meta.fields if
                             f.name != 'id' and f.name != 'total_received']
            return super(BookingAccount, self).save(update_fields=update_fields, **kwargs)

    # Business methods:

    def get_balance(self, *, confirmed_only: bool, allow_deposits: bool, price_checker: PriceChecker):
        """
        Gets the balance to pay on the account.
        If confirmed_only=True, then only bookings that are confirmed
        (no expiration date) are included as 'received goods'.
        If allow_deposits=True, then bookings that only require deposits
        at this point in time will only count for the deposit amount.

        price_checker is used to look up deposit prices when needed,
        and it is a non-optional argument to encourage the most efficient
        usage patterns, even though it isn't needed for every path.
        """
        today = date.today()
        # Use of _prefetched_objects_cache is necessary to support the
        # booking_secretary_reports view efficiently
        if hasattr(self, '_prefetched_objects_cache') and 'bookings' in self._prefetched_objects_cache:
            payable_bookings = [
                booking for booking in self._prefetched_objects_cache['bookings']
                if booking.is_payable(confirmed_only=confirmed_only)
            ]
        else:
            payable_bookings = list(self.bookings.payable(confirmed_only=confirmed_only))

        total = Decimal('0.00')
        for booking in payable_bookings:
            total += booking.amount_now_due(today,
                                            allow_deposits=allow_deposits,
                                            price_checker=price_checker)

        return total - self.total_received

    def get_balance_full(self, *, price_checker: Optional[PriceChecker] = None):
        return self.get_balance(confirmed_only=False, allow_deposits=False,
                                price_checker=price_checker or PriceChecker())

    def get_balance_due_now(self, *, price_checker: PriceChecker):
        return self.get_balance(confirmed_only=False, allow_deposits=True, price_checker=price_checker)

    def admin_balance(self):
        return self.get_balance_full()
    admin_balance.short_description = 'balance'
    admin_balance = property(admin_balance)

    def receive_payment(self, amount):
        """
        Adds the amount to the account's total_received field.  This should only
        ever be called by the 'process_all_payments' function. Client code
        should use the 'send_payment' function.
        """
        # See process_all_payments function for an explanation of the above

        # = Receiving payments =
        #
        # This system needs to be robust, and cope with all kinds of user error, and
        # things not matching up. The essential philosophy of this code is to assume the
        # worst, most complicated scenario, and this will then easily handle the more
        # simple case where everything matches up as a special case.
        #
        # For online bookings, when the user clicks 'book place', the places are
        # marked as 'booked', but with a 'booking_expires' field set to a
        # non-NULL timestamp, so that the bookings will expire if the user does
        # not complete payment.
        #
        # If the user does complete payment, the booking_expires field must be cleared,
        # so that the place becomes 'confirmed'.
        #
        # When an online payment is received, django-paypal creates a record
        # and a signal handler indirectly calls this method which must update
        # the 'total_received' field.
        #
        # At the same time we also need to set the 'Booking.booking_expires'
        # field of relevant Booking objects to null, so that the places are
        # securely booked.
        #
        # There are a number of scenarios where the amount paid doesn't cover
        # the total amount due:
        #
        # 1) user fiddles with the form client side and alters the amount
        # 2) user starts paying for one place, then books another place in a different
        # tab/window
        #
        # It is also possible for a place to be partially paid for, yet booked e.g. if a
        # user selects a discount for which they were not eligible, and pays. This is then
        # discovered, and the 'amount due' for that place is altered by an admin.
        #
        # Also, users have the option to pay only the deposit for a booking.
        #
        # So, we need a method to distribute any incoming payment so that we stop the
        # booked place from expiring. It is better to be too generous than too stingy in
        # stopping places from expiring, because:
        #
        # * on camp we can generally cope with one too many campers
        # * we don't want people slipping off the camp lists by accident
        # * we can always check whether people still have money outstanding by just checking
        #   the total amount paid against the total amount due.
        #
        # Therefore, we ignore the partially paid case, and for distributing payment treat
        # any place which is 'booked' with no 'booking_expires' as fully paid.
        #
        # When a payment is received, we don't know which place it is for, and
        # in general it could be for any combination of the places that need
        # payment. There could also be money in the account that is still
        # 'unclaimed'. So, for simplicity we simply go through all places which
        # are 'booked' and have a 'booking_expires' date, starting with the
        # earliest 'booking_expires', on the assumption that we will get payment
        # for that one first.
        #
        # The manual booking process, which uses the admin to record cheque
        # payments, uses exactly the same process, although it is a different
        # payment object which triggers the process.

        # Use update and F objects to avoid concurrency problems
        BookingAccount.objects.filter(id=self.id).update(total_received=models.F('total_received') + amount)

        # Need new data from DB:
        acc = BookingAccount.objects.get(id=self.id)
        self.total_received = acc.total_received

        self.distribute_balance()

    def distribute_balance(self):
        """
        Distribute any money in the account to mark unconfirmed places as
        confirmed.
        """
        # To satisfy PriceChecker performance requirements it's easier
        # to get all bookings up front:
        all_account_bookings = list(self.bookings.all().select_related('camp'))

        # Bookings we might want to confirm.
        # Order by booking_expires ascending i.e. earliest first.
        candidate_bookings = sorted([b for b in all_account_bookings if not b.is_confirmed],
                                    key=lambda b: b.booking_expires)
        price_checker = PriceChecker(expected_years=[b.camp.year for b in all_account_bookings])
        confirmed_bookings = []
        # In order to distribute funds, need to take into account the total
        # amount in the account that is not required by already confirmed places
        existing_balance = self.get_balance(confirmed_only=True, allow_deposits=True, price_checker=price_checker)
        # The 'pot' is the amount we have as excess and can use to mark places
        # as confirmed.
        pot = -existing_balance
        today = date.today()
        for booking in candidate_bookings:
            if pot <= 0:
                break
            amount = booking.amount_now_due(today, allow_deposits=True, price_checker=price_checker)
            if amount <= pot:
                booking.confirm()
                booking.save()
                confirmed_bookings.append(booking)
                pot -= amount

        if confirmed_bookings:
            places_confirmed.send(self, bookings=confirmed_bookings, payment_received=True)

    def get_pending_payment_total(self, now=None):
        if now is None:
            now = timezone.now()

        custom = build_paypal_custom_field(self)
        all_payments = PayPalIPN.objects.filter(
            custom=custom,
        )
        pending_payments = all_payments.filter(
            payment_status='Pending',
            payment_date__gt=now - timedelta(days=3 * 30),  # old ones don't count
        )
        completed_payments = all_payments.filter(
            payment_status='Completed',
        )
        uncompleted_pending_payments = pending_payments.exclude(
            txn_id__in=[ipn.txn_id for ipn in completed_payments])

        total = uncompleted_pending_payments.aggregate(total=models.Sum('mc_gross'))['total']
        if total is None:
            return Decimal('0.00')
        return total

    def get_address_display(self):
        return "\n".join(v for v in [self.address_line1,
                                     self.address_line2,
                                     self.address_city,
                                     self.address_county,
                                     self.address_country.code if self.address_country else None,
                                     ] if v)

    @property
    def include_in_mailings(self):
        if self.subscribe_to_mailings is None:
            # GDPR. We have not obtained an answer to this question.
            # For postal mailings, by legitimate interest we
            # are allowed to assume 'Yes'
            return True
        else:
            return self.subscribe_to_mailings


class BookingQuerySet(models.QuerySet):

    def for_year(self, year):
        return self.filter(camp__year__exact=year)

    def in_basket(self):
        return self._ready_to_book(False)

    def on_shelf(self):
        return self._ready_to_book(True)

    def _ready_to_book(self, shelved):
        qs = self.filter(shelved=shelved)
        return qs.filter(state=BookingState.INFO_COMPLETE) | qs.filter(state=BookingState.APPROVED)

    def booked(self):
        return self.filter(state=BookingState.BOOKED)

    def in_basket_or_booked(self):
        return self.in_basket() | self.booked()

    def confirmed(self):
        return self.filter(state=BookingState.BOOKED,
                           booking_expires__isnull=True)

    def unconfirmed(self):
        return self.filter(state=BookingState.BOOKED,
                           booking_expires__isnull=False)

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
        return (self.filter(state__in=[BookingState.CANCELLED_DEPOSIT_KEPT,
                                       BookingState.CANCELLED_HALF_REFUND]) |
                (self.confirmed() if confirmed_only else self.booked()))

    def cancelled(self):
        return self.filter(state__in=[BookingState.CANCELLED_DEPOSIT_KEPT,
                                      BookingState.CANCELLED_HALF_REFUND,
                                      BookingState.CANCELLED_FULL_REFUND])

    def need_approving(self):
        # See also Booking.approval_reasons()
        qs = self.filter(state=BookingState.INFO_COMPLETE).select_related('camp')
        qs_custom_price = qs.filter(price_type=PriceType.CUSTOM)
        qs_serious_illness = qs.filter(serious_illness=True)
        # See also Booking.age_on_camp()
        qs_too_young = qs.extra(where=[
            """ "bookings_booking"."date_of_birth" > """
            """ date(CAST(("cciwmain_camp"."year" - "cciwmain_camp"."minimum_age") as text) || '-08-31')"""
        ])
        qs_too_old = qs.extra(where=[
            """ "bookings_booking"."date_of_birth" <= """
            """ date(CAST(("cciwmain_camp"."year" - "cciwmain_camp"."maximum_age" - 1) as text) || '-08-31')"""
        ])
        qs = qs_custom_price | qs_serious_illness | qs_too_old | qs_too_young
        return qs


class BookingManagerBase(models.Manager):

    def get_queryset(self):
        return super(BookingManagerBase, self).get_queryset().select_related(
            'camp',
            'account'
        )


BookingManager = BookingManagerBase.from_queryset(BookingQuerySet)


class Booking(models.Model):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='bookings')

    # Booking details - from user
    camp = models.ForeignKey(Camp,
                             on_delete=models.CASCADE,
                             related_name='bookings')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=Sex.choices)
    date_of_birth = models.DateField()
    address_line1 = models.CharField("address line 1", max_length=255)
    address_line2 = models.CharField("address line 2", max_length=255, blank=True)
    address_city = models.CharField("town/city", max_length=255)
    address_county = models.CharField("county/state", max_length=255, blank=True)
    address_country = CountryField("country", null=True)
    address_post_code = models.CharField("post code", max_length=10)

    phone_number = models.CharField(blank=True, max_length=22)
    email = models.EmailField(blank=True)
    church = models.CharField("name of church", max_length=100, blank=True)
    south_wales_transport = models.BooleanField("require transport from South Wales",
                                                blank=True, default=False)

    # Contact - from user
    contact_name = models.CharField("contact name", max_length=255, blank=True)
    contact_line1 = models.CharField("address line 1", max_length=255)
    contact_line2 = models.CharField("address line 2", max_length=255, blank=True)
    contact_city = models.CharField("town/city", max_length=255)
    contact_county = models.CharField("county/state", max_length=255, blank=True)
    contact_country = CountryField("country", null=True)
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
    gp_country = CountryField("country", null=True)
    gp_post_code = models.CharField("post code", max_length=10)
    gp_phone_number = models.CharField("GP phone number", max_length=22)

    # Medical details - from user
    medical_card_number = models.CharField("NHS number", max_length=100)  # no idea how long it should be
    last_tetanus_injection_date = models.DateField(null=True, blank=True)
    allergies = models.TextField(blank=True)
    regular_medication_required = models.TextField(blank=True)
    illnesses = models.TextField("Medical conditions", blank=True)
    can_swim_25m = models.BooleanField(blank=True, default=False,
                                       verbose_name="Can the camper swim 25m?")
    learning_difficulties = models.TextField(blank=True)
    serious_illness = models.BooleanField(blank=True, default=False)

    # Agreement - from user
    agreement = models.BooleanField(default=False)

    # Price - partly from user (must fit business rules)
    price_type = models.PositiveSmallIntegerField(choices=[(pt, pt.label) for pt in BOOKING_PLACE_PRICE_TYPES])
    early_bird_discount = models.BooleanField(default=False, help_text="Online bookings only")
    booked_at = models.DateTimeField(null=True, blank=True, help_text="Online bookings only")
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - user driven
    shelved = models.BooleanField(default=False,
                                  help_text="Used by user to put on 'shelf'")

    # State - internal
    state = models.IntegerField(choices=BookingState.choices,
                                help_text=mark_safe(
                                    "<ul>"
                                    "<li>To book, set to 'Booked' <b>and</b> ensure 'Booking expires' is empty</li>"
                                    "<li>For people paying online who have been stopped (e.g. due to having a custom discount or serious illness or child too young etc.), set to 'Manually approved' to allow them to book and pay</li>"
                                    "<li>If there are queries before it can be booked, set to 'Information complete'</li>"
                                    "</ul>"))

    created = models.DateTimeField(default=timezone.now)
    booking_expires = models.DateTimeField(null=True, blank=True)
    created_online = models.BooleanField(blank=True, default=False)

    objects = BookingManager()

    class Meta:
        ordering = ['-created']
        base_manager_name = 'objects'

    # Methods

    def __str__(self):
        return f"{self.name}, {self.camp.url_id}, {self.account}"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    # Main business rules here
    def save_for_account(self, booking_account):
        """
        Saves the booking for an account that is creating/editing online
        """
        self.account = booking_account
        self.early_bird_discount = False  # We only allow this to be True when booking
        self.auto_set_amount_due()
        self.state = BookingState.INFO_COMPLETE
        if self.id is None:
            self.created_online = True
        self.save()

    def is_payable(self, *, confirmed_only: bool):
        # See also BookingQuerySet.payable()
        return (self.state in [BookingState.CANCELLED_DEPOSIT_KEPT,
                               BookingState.CANCELLED_HALF_REFUND] or
                (self.is_confirmed if confirmed_only else self.is_booked))

    @property
    def is_booked(self):
        return self.state == BookingState.BOOKED

    @property
    def is_confirmed(self):
        return self.is_booked and self.booking_expires is None

    def expected_amount_due(self):
        if self.price_type == PriceType.CUSTOM:
            return None
        if self.state == BookingState.CANCELLED_DEPOSIT_KEPT:
            return Price.objects.get(year=self.camp.year,
                                     price_type=PriceType.DEPOSIT).price
        elif self.state == BookingState.CANCELLED_FULL_REFUND:
            return Decimal('0.00')
        else:
            amount = Price.objects.get(year=self.camp.year,
                                       price_type=self.price_type).price
            # For booking 2015 and later, this is not needed, but it kept in
            # case we need to query the expected amount due for older bookings.
            if self.south_wales_transport:
                amount += Price.objects.get(price_type=PriceType.SOUTH_WALES_TRANSPORT,
                                            year=self.camp.year).price

            if self.early_bird_discount:
                amount -= Price.objects.get(price_type=PriceType.EARLY_BIRD_DISCOUNT,
                                            year=self.camp.year).price

            # For booking 2015 and later, there are no half refunds,
            # but this is kept in in case we need to query the expected amount due for older
            # bookings.
            if self.state == BookingState.CANCELLED_HALF_REFUND:
                amount = amount / 2

            return amount

    def auto_set_amount_due(self):
        amount = self.expected_amount_due()
        if amount is None:
            # This happens for PriceType.CUSTOM
            if self.amount_due is None:
                self.amount_due = Decimal('0.00')
            # Otherwise - should leave as it was.
        else:
            self.amount_due = amount

    def amount_now_due(self, today: date, *, allow_deposits, price_checker: PriceChecker):
        # Amount due at this point of time. If allow_deposits=True, we take into
        # account the fact that only a deposit might be due. Otherwise we ignore
        # deposits (which means that the current date is also ignored)
        cutoff = today + timedelta(days=settings.BOOKING_FULL_PAYMENT_DUE_DAYS)
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
        return Price.objects.get(price_type=PriceType.EARLY_BIRD_DISCOUNT,
                                 year=self.camp.year).price

    def age_on_camp(self):
        # Age is calculated based on school years, i.e. age on 31st August
        # See also BookingManager.need_approving()
        return relativedelta(self.age_base_date(), self.date_of_birth).years

    def age_base_date(self):
        return date(self.camp.year, 8, 31)

    def is_too_young(self):
        return self.age_on_camp() < self.camp.minimum_age

    def is_too_old(self):
        return self.age_on_camp() > self.camp.maximum_age

    def approval_reasons(self):
        """
        Gets a list of human-readable reasons why the booking needs manual approval.
        """
        # See also BookingManager.need_approving()
        reasons = []
        if self.serious_illness:
            reasons.append("Serious illness")
        if self.is_custom_discount():
            reasons.append("Custom discount")
        if self.is_too_young():
            reasons.append("Too young")
        if self.is_too_old():
            reasons.append("Too old")
        return reasons

    def get_available_discounts(self, now):
        retval = []
        if self.can_have_early_bird_discount(booked_at=now):
            retval.append(("Early bird discount if booked now",
                           Price.objects.get(year=self.camp.year,
                                             price_type=PriceType.EARLY_BIRD_DISCOUNT).price))
        return retval

    def get_booking_problems(self, booking_sec=False):
        """
        Returns a two tuple (errors, warnings).

        'errors' is a list of reasons why booking cannot be done. If this is
        empty, then it can be booked.

        'warnings' is a list of possible problems that don't stop booking.

        If booking_sec=True, it shows the problems as they should be seen by the
        booking secretary.
        """
        if self.state == BookingState.APPROVED and not booking_sec:
            return ([], [])

        return (self.get_booking_errors(booking_sec=booking_sec),
                self.get_booking_warnings(booking_sec=booking_sec))

    def get_booking_errors(self, booking_sec=False):
        errors = []

        # Custom price - not auto bookable
        if self.price_type == PriceType.CUSTOM:
            errors.append("A custom discount needs to be arranged by the booking secretary")

        relevant_bookings = self.account.bookings.for_year(self.camp.year).in_basket_or_booked()
        relevant_bookings_excluding_self = relevant_bookings.exclude(first_name=self.first_name,
                                                                     last_name=self.last_name)
        relevant_bookings_limited_to_self = relevant_bookings.filter(first_name=self.first_name,
                                                                     last_name=self.last_name)

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
            if not (relevant_bookings_excluding_self
                    .filter(price_type=PriceType.FULL)
                    ).exists():
                errors.append("You cannot use a 2nd child discount unless you have "
                              "another child at full price. Please edit the place details "
                              "and choose an appropriate price type.")

        if self.price_type == PriceType.THIRD_CHILD:
            qs = (relevant_bookings_excluding_self.filter(price_type=PriceType.FULL) |
                  relevant_bookings_excluding_self.filter(price_type=PriceType.SECOND_CHILD))
            if qs.count() < 2:
                errors.append("You cannot use a 3rd child discount unless you have "
                              "two other children without this discount. Please edit the "
                              "place details and choose an appropriate price type.")

        if self.price_type in [PriceType.SECOND_CHILD, PriceType.THIRD_CHILD]:
            qs = relevant_bookings_limited_to_self
            qs = qs.filter(price_type=PriceType.SECOND_CHILD) | qs.filter(price_type=PriceType.THIRD_CHILD)
            if qs.count() > 1:
                errors.append("If a camper goes on multiple camps, only one place may use a 2nd/3rd child discount.")

        # serious illness
        if self.serious_illness:
            errors.append("Must be approved by leader due to serious illness/condition")

        # Check age.
        camper_age = self.age_on_camp()
        age_base = self.age_base_date().strftime("%e %B %Y")
        if self.is_too_young():
            errors.append(f"Camper will be {camper_age} which is below the minimum age ({self.camp.minimum_age}) on {age_base}")

        if self.is_too_old():
            errors.append(f"Camper will be {camper_age} which is above the maximum age ({self.camp.maximum_age}) on {age_base}")

        # Check place availability
        places_left, places_left_male, places_left_female = self.camp.get_places_left()

        # We only want one message about places not being available, and the
        # order here is important - if there are no places full stop, we don't
        # want to display message about there being no places for boys etc.
        places_available = True

        # Simple - no places left
        if places_left <= 0:
            errors.append("There are no places left on this camp.")
            places_available = False

        SEXES = [
            (Sex.MALE, 'boys', places_left_male),
            (Sex.FEMALE, 'girls', places_left_female),
        ]

        if places_available:
            for sex_const, sex_label, places_left_for_sex in SEXES:
                if self.sex == sex_const and places_left_for_sex <= 0:
                    errors.append(f"There are no places left for {sex_label} on this camp.")
                    places_available = False
                    break

        if places_available:
            # Complex - need to check the other places that are about to be booked.
            # (if there is one place left, and two campers for it, we can't say that
            # there are enough places)
            same_camp_bookings = self.account.bookings.filter(camp=self.camp).in_basket()
            places_to_be_booked = same_camp_bookings.count()

            if places_left < places_to_be_booked:
                errors.append("There are not enough places left on this camp "
                              "for the campers in this set of bookings.")
                places_available = False

            if places_available:
                for sex_const, sex_label, places_left_for_sex in SEXES:
                    if self.sex == sex_const:
                        places_to_be_booked_for_sex = same_camp_bookings.filter(sex=sex_const).count()
                        if places_left_for_sex < places_to_be_booked_for_sex:
                            errors.append("There are not enough places for {0} left on this camp "
                                          "for the campers in this set of bookings.".format(sex_label))
                            places_available = False
                            break

        if self.south_wales_transport and not self.camp.south_wales_transport_available:
            errors.append("Transport from South Wales is not available for this camp, or all places have been taken already.")

        if booking_sec and self.price_type != PriceType.CUSTOM:
            expected_amount = self.expected_amount_due()
            if self.amount_due != expected_amount:
                errors.append(f"The 'amount due' is not the expected value of £{expected_amount}.")

        if booking_sec and not self.created_online:
            if self.early_bird_discount:
                errors.append("The early bird discount is only allowed for bookings created online.")

        # Don't want warnings for booking sec when a booked place is edited
        # after the cutoff date, so we allow self.booked_at to be used here:
        on_date = self.booked_at if self.is_booked and self.booked_at is not None else date.today()

        if not self.camp.open_for_bookings(on_date):
            if on_date >= self.camp.end_date:
                msg = "This camp has already finished."
            elif on_date >= self.camp.start_date:
                msg = "This camp is closed for bookings because it has already started."
            else:
                msg = "This camp is closed for bookings."
            errors.append(msg)

        return errors

    def get_booking_warnings(self, booking_sec=False):
        warnings = []

        if self.account.bookings.filter(first_name=self.first_name, last_name=self.last_name, camp=self.camp).exclude(id=self.id):
            warnings.append(f"You have entered another set of place details for a camper "
                            f"called '{self.name}' on camp {self.camp.name}. Please ensure you don't book multiple "
                            f"places for the same camper!")

        relevant_bookings = self.account.bookings.for_year(self.camp.year).in_basket_or_booked()

        if self.price_type == PriceType.FULL:
            full_pricers = relevant_bookings.filter(price_type=PriceType.FULL)
            names = sorted(set([b.name for b in full_pricers]))
            if len(names) > 1:
                pretty_names = ', '.join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at 'Full price'. "
                if len(names) == 2:
                    warning += f"If {pretty_names} are from the same family, one is eligible for the 2nd child discount."
                else:
                    warning += f"If {pretty_names} are from the same family, one or more is eligible for the 2nd or 3rd child discounts."

                warnings.append(warning)

        if self.price_type == PriceType.SECOND_CHILD:
            second_childers = relevant_bookings.filter(price_type=PriceType.SECOND_CHILD)
            names = sorted(set([b.name for b in second_childers]))
            if len(names) > 1:
                pretty_names = ', '.join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at '2nd child discount'. "
                if len(names) == 2:
                    warning += (f"If {pretty_names} are from the same family, one is eligible "
                                f"for the 3rd child discount.")
                else:
                    warning += (f"If {pretty_names} are from the same family, {len(names) - 1} are eligible "
                                f"for the 3rd child discount.")

                warnings.append(warning)

        return warnings

    def confirm(self):
        self.booking_expires = None

    def expire(self):
        self.booking_expires = None
        self.state = BookingState.INFO_COMPLETE
        self.early_bird_discount = False
        self.booked_at = None
        self.auto_set_amount_due()

    def is_user_editable(self):
        return self.state == BookingState.INFO_COMPLETE

    def is_custom_discount(self):
        return self.price_type == PriceType.CUSTOM

    def get_contact_email(self):
        if self.email:
            return self.email
        elif self.account_id is not None:
            return self.account.email

    def get_address_display(self):
        return "\n".join(v for v in [self.address_line1,
                                     self.address_line2,
                                     self.address_city,
                                     self.address_county,
                                     self.address_country.code if self.address_country else None,
                                     self.address_post_code,
                                     ] if v)

    def get_contact_address_display(self):
        return "\n".join(v for v in [self.contact_name,
                                     self.contact_line1,
                                     self.contact_line2,
                                     self.contact_city,
                                     self.contact_county,
                                     self.contact_country.code if self.contact_country else None,
                                     self.contact_post_code,
                                     ] if v)

    def get_gp_address_display(self):
        return "\n".join(v for v in [self.gp_line1,
                                     self.gp_line2,
                                     self.gp_city,
                                     self.gp_county,
                                     self.gp_country.code if self.gp_country else None,
                                     self.gp_post_code,
                                     ] if v)


@transaction.atomic
def book_basket_now(bookings):
    """
    Book a basket of bookings, returning True if successful,
    False otherwise.
    """
    bookings = list(bookings)

    now = timezone.now()
    for b in bookings:
        if len(b.get_booking_problems()[0]) > 0:
            return False

    # Serialize access to this function, to stop more places than available
    # being booked:
    years = set([b.camp.year for b in bookings])
    assert len(years) == 1
    year_bookings = Booking.objects.for_year(list(years)[0]).select_for_update()
    list(year_bookings)  # evaluate query to apply lock, don't need the result

    for b in bookings:
        b.booked_at = now
        # Early bird discounts are only applied for online bookings, and
        # this needs to be re-assessed if a booking expires and is later
        # booked again. Therefore it makes sense to put the logic here
        # rather than in the Booking model.
        b.early_bird_discount = b.can_have_early_bird_discount()
        b.auto_set_amount_due()
        b.state = BookingState.BOOKED
        b.booking_expires = now + timedelta(1)  # 24 hours
        b.save()

    # In some cases we may have enough money to pay for places from money in
    # account. Since a payment will not be needed or received, we need to
    # make sure these don't expire.
    seen_accounts = set()
    for b in bookings:
        if b.account_id in seen_accounts:
            continue
        b.account.distribute_balance()
        seen_accounts.add(b.account_id)

    return True


def get_early_bird_cutoff_date(year):
    # 1st May
    return timezone.get_default_timezone().localize(datetime(year, 5, 1))


def early_bird_is_available(year, booked_at_date):
    return booked_at_date < get_early_bird_cutoff_date(year)


def any_bookings_possible(year):
    camps = Camp.objects.filter(year=year)
    return any(c.get_places_left()[0] > 0 and c.is_open_for_bookings
               for c in camps)


def is_booking_open(year):
    """
    When passed a given year, returns True if booking is open.
    """
    return ((Price.objects.required_for_booking().filter(year=year).count() ==
             len(REQUIRED_PRICE_TYPES)) and
            Camp.objects.filter(year=year).exists())


is_booking_open_thisyear = lambda: is_booking_open(common.get_thisyear())


def booking_report_by_camp(year):
    """
    Returns list of camps with annotations:
      confirmed_bookings
      confirmed_bookings_boys
      confirmed_bookings_girls
    """
    camps = Camp.objects.filter(year=year).prefetch_related(Prefetch('bookings',
                                                                     queryset=Booking.objects.booked(),
                                                                     to_attr='booked_places'))
    # Do some filtering in Python to avoid multiple db hits
    for c in camps:
        c.confirmed_bookings = [b for b in c.booked_places if b.is_confirmed]
        c.confirmed_bookings_boys = [b for b in c.confirmed_bookings if b.sex == Sex.MALE]
        c.confirmed_bookings_girls = [b for b in c.confirmed_bookings if b.sex == Sex.FEMALE]
    return camps


def outstanding_bookings_with_fees(year):
    """
    Returns bookings that have outstanding amounts due (or owed by us),
    with `calculated_balance` and `calculated_balance_due` annotations.
    """
    bookings = Booking.objects.for_year(year)
    # We need to include 'full refund' cancelled bookings in case they overpaid,
    # as well as all 'payable' bookings.
    bookings = bookings.payable(confirmed_only=True) | bookings.cancelled()

    # 3 concerns:
    # 1) people who have overpaid. This must be calculated with respect to the total amount due
    #    on the account.
    # 2) people who have underpaid:
    #    a) with respect to the total amount due
    #    b) with respect to the total amount due at this point in time,
    #       allowing for the fact that up to a certain point,
    #       only the deposit is actually required.
    #
    # People in group 2b) possibly need to be chased. They are not highlighted here - TODO

    bookings = bookings.order_by('account__name', 'account__id', 'first_name', 'last_name')
    bookings = list(
        bookings
        .select_related('camp__camp_name', 'account')
        .prefetch_related('account__bookings__camp')
    )

    counts = defaultdict(int)
    for b in bookings:
        counts[b.account_id] += 1

    price_checker = PriceChecker(expected_years=[b.camp.year for b in bookings])
    outstanding = []
    for b in bookings:
        b.count_for_account = counts[b.account_id]
        if not hasattr(b.account, 'calculated_balance'):
            b.account.calculated_balance = b.account.get_balance(confirmed_only=True,
                                                                 allow_deposits=False,
                                                                 price_checker=price_checker)
            b.account.calculated_balance_due = b.account.get_balance(confirmed_only=True,
                                                                     allow_deposits=True,
                                                                     price_checker=price_checker)

            if b.account.calculated_balance_due > 0 or b.account.calculated_balance < 0:
                outstanding.append(b)

    return outstanding


# --- Payments ---

class PaymentManager(models.Manager):

    def get_queryset(self):
        return super(PaymentManager, self).get_queryset().select_related(
            'account',
            'source',
            'source__manual_payment',
            'source__refund_payment',
            'source__account_transfer_payment',
            'source__ipn_payment',
        )

    def create(self, source_instance=None, **kwargs):
        if source_instance is not None:
            source = PaymentSource.from_source_instance(source_instance)
            kwargs['source'] = source
        return super(PaymentManager, self).create(**kwargs)


# The Payment object keeps track of all the payments that need to be or have
# been credited to an account. It also acts as a log of everything that has
# happened to the BookingAccount.total_received field. Payment objects are never
# modified or deleted - if, for example, a ManualPayment object is deleted
# because of an entry error, a new (negative) Payment object is created.

class Payment(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    account = models.ForeignKey(BookingAccount,
                                related_name='payments',
                                on_delete=models.CASCADE)
    source = models.OneToOneField('PaymentSource',
                                  null=True, blank=True,
                                  on_delete=models.SET_NULL)
    processed = models.DateTimeField(null=True)
    created = models.DateTimeField()

    objects = PaymentManager()

    class Meta:
        base_manager_name = 'objects'

    def __str__(self):
        if self.source_id is not None and hasattr(self.source, 'payment_description'):
            retval = self.source.payment_description
        else:
            retval = "Payment: {amount} {from_or_to} {name} via {type}".format(
                amount=abs(self.amount),
                from_or_to='from' if self.amount > 0 else 'to',
                name=self.account.name,
                type=self.payment_type,
            )

        return retval

    @property
    def payment_type(self):
        if self.source_id is None:
            return "[deleted]"

        return self.source.payment_type


class ManualPaymentManager(models.Manager):

    def get_queryset(self):
        return super(ManualPaymentManager, self).get_queryset().select_related('account')


class ManualPaymentBase(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created = models.DateTimeField(default=timezone.now)
    payment_type = models.PositiveSmallIntegerField(choices=ManualPaymentType.choices,
                                                    default=ManualPaymentType.CHEQUE)

    class Meta:
        abstract = True
        base_manager_name = 'objects'


class ManualPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='manual_payments')

    objects = ManualPaymentManager()

    class Meta:
        base_manager_name = 'objects'

    def __str__(self):
        return f"Manual payment of £{self.amount} from {self.account}"


class RefundPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='refund_payments')

    objects = ManualPaymentManager()

    class Meta:
        base_manager_name = 'objects'

    def __str__(self):
        return f"Refund payment of £{self.amount} to {self.account}"


class AccountTransferPayment(NoEditMixin, models.Model):
    from_account = models.ForeignKey(BookingAccount,
                                     on_delete=models.CASCADE,
                                     related_name='transfer_from_payments')
    to_account = models.ForeignKey(BookingAccount,
                                   on_delete=models.CASCADE,
                                   related_name='transfer_to_payments')
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "{0} from {1} to {2} on {3}".format(self.amount,
                                                   self.from_account, self.to_account,
                                                   self.created)

    @property
    def payment_description(self):
        return "Payment: {0} transferred from {1} to {2}".format(self.amount,
                                                                 self.from_account,
                                                                 self.to_account)


# This model abstracts the different types of payment that can be the source for
# Payment. The real 'source' is the instance pointed to by one of the FKs it
# contains.
class PaymentSource(models.Model):
    manual_payment = models.OneToOneField(ManualPayment,
                                          null=True, blank=True,
                                          on_delete=models.CASCADE)
    refund_payment = models.OneToOneField(RefundPayment,
                                          null=True, blank=True,
                                          on_delete=models.CASCADE)
    # There are two PaymentSource items for each AccountTransferPayment
    # so this is FK not OneToOneField
    account_transfer_payment = models.ForeignKey(AccountTransferPayment,
                                                 null=True, blank=True,
                                                 on_delete=models.CASCADE)
    ipn_payment = models.OneToOneField(PayPalIPN,
                                       null=True, blank=True,
                                       on_delete=models.CASCADE)

    MODEL_MAP = {
        ManualPayment: 'manual_payment',
        RefundPayment: 'refund_payment',
        AccountTransferPayment: 'account_transfer_payment',
        PayPalIPN: 'ipn_payment',
    }

    def save(self, *args, **kwargs):
        self._assert_one_source()
        super(PaymentSource, self).save()

    @property
    def payment_type(self):
        if self.manual_payment_id is not None:
            return self.manual_payment.get_payment_type_display()
        elif self.refund_payment_id is not None:
            return "Refund " + self.refund_payment.get_payment_type_display()
        elif self.account_transfer_payment_id is not None:
            return "Account transfer"
        elif self.ipn_payment_id is not None:
            return "PayPal"
        else:
            raise ValueError(f"No related object for PaymentSource {self.id}")

    def _assert_one_source(self):
        attrs = [f'{a}_id' for a in self.MODEL_MAP.values()]
        if not [getattr(self, a) for a in attrs].count(None) == len(attrs) - 1:
            raise AssertionError("PaymentSource must have exactly one payment FK set")

    @classmethod
    def from_source_instance(cls, source_instance):
        """
        Create a PaymentSource from a real payment model
        """
        source_cls = source_instance.__class__
        if source_cls not in cls.MODEL_MAP:
            raise AssertionError(f"Can't create PaymentSource for {source_cls}")
        attr_name_for_model = cls.MODEL_MAP[source_cls]
        return cls.objects.create(**{attr_name_for_model: source_instance})


def send_payment(amount, to_account, from_obj):
    Payment.objects.create(amount=amount,
                           account=to_account,
                           source_instance=from_obj,
                           processed=None,
                           created=timezone.now())
    process_all_payments()


def build_paypal_custom_field(account):
    return f"account:{account.id};"


def parse_paypal_custom_field(custom):
    m = re.match(r"account:(\d+);", custom)
    if m is None:
        return None

    try:
        return BookingAccount.objects.get(id=int(m.groups()[0]))
    except BookingAccount.DoesNotExist:
        return None


def expire_bookings(now=None):
    if now is None:
        now = timezone.now()

    # For the warning, we send out between 12 and 13 hours before booking
    # expires.  This relies on this job being run once an hour, and only
    # once an hour.
    nowplus12h = now + timedelta(0, 3600 * 12)
    nowplus13h = now + timedelta(0, 3600 * 13)

    unconfirmed = Booking.objects.unconfirmed().order_by('account')
    to_warn = unconfirmed.filter(booking_expires__lte=nowplus13h,
                                 booking_expires__gte=nowplus12h)
    to_expire = unconfirmed.filter(booking_expires__lte=now)

    for booking_set, expired in [(to_expire, True),
                                 (to_warn, False)]:
        groups = []
        last_account_id = None
        for b in booking_set:
            if last_account_id is None or b.account_id != last_account_id:
                group = []
                groups.append(group)
            group.append(b)
            last_account_id = b.account_id

        for group in groups:
            account = group[0].account
            if account.get_pending_payment_total(now=now) > Decimal("0.00"):
                continue

            if expired:
                for b in group:
                    b.expire()
                    b.save()
            send_booking_expiry_mail(account, group, expired)


@transaction.atomic
def process_one_payment(payment):
    payment.account.receive_payment(payment.amount)
    payment.processed = timezone.now()
    # Payment.processed is ignored in Payment.save, so do update
    Payment.objects.filter(id=payment.id).update(processed=payment.processed)


# When processing payments, we need to alter the BookingAccount.total_received
# field, and may need to deal with concurrency, to avoid race conditions that
# would cause this field to have the wrong value.
#
# We arrange for updates to BookingAccount.total_received to be serialised
# using the function below.
#
# To support this, the Payment model keeps track of payments to be credited
# against an account. Any function that needs to transfer funds into an account
# uses 'cciw.bookings.models.send_payment', which creates Payment objects for
# later processing, rather than calling BookingAccount.receive_payment directly.

@transaction.atomic
def process_all_payments():
    # Use select_for_update to serialize usages of this function.
    for payment in (Payment.objects
                    .select_related(None)
                    .select_for_update()
                    .filter(processed__isnull=True).order_by('created')):
        process_one_payment(payment)


def most_recent_booking_year():
    booking = Booking.objects.booked().order_by('-camp__year').select_related('camp').first()
    if booking:
        return booking.camp.year
    else:
        return None


from . import hooks  # NOQA isort:skip
