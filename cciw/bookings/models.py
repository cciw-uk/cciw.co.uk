# -*- coding: utf-8 -*-
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from django_countries.fields import CountryField
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import Lock

from .signals import places_confirmed

# = Business rules =
#
# Business rules are implemented in relevant models and managers.
#
# Some business logic duplicated in
# cciw.officers.views.booking_secretary_reports for performance reasons.


SEX_MALE, SEX_FEMALE = 'm', 'f'
SEXES = [
    (SEX_MALE, 'Male'),
    (SEX_FEMALE, 'Female'),
]

# Price types that can be selected for a booking
PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, PRICE_SOUTH_WALES_TRANSPORT, PRICE_DEPOSIT, PRICE_EARLY_BIRD_DISCOUNT = range(0, 7)
BOOKING_PLACE_PRICE_TYPES = [
    (PRICE_FULL, 'Full price'),
    (PRICE_2ND_CHILD, '2nd child discount'),
    (PRICE_3RD_CHILD, '3rd child discount'),
    (PRICE_CUSTOM, 'Custom discount'),
]

# Price types that are used by Price model
VALUED_PRICE_TYPES = [(v, d) for (v, d) in BOOKING_PLACE_PRICE_TYPES if v is not PRICE_CUSTOM] + \
    [(PRICE_SOUTH_WALES_TRANSPORT, 'South wales transport surcharge (pre 2015)'),
     (PRICE_DEPOSIT, 'Deposit'),
     (PRICE_EARLY_BIRD_DISCOUNT, 'Early bird discount'),
     ]

# From 2015 onwards, we don't have South Wales transport. But we might
# want to keep info about prices etc. for a few years.
REQUIRED_PRICE_TYPES = [(v, d) for (v, d) in VALUED_PRICE_TYPES if v != PRICE_SOUTH_WALES_TRANSPORT]


BOOKING_INFO_COMPLETE, BOOKING_APPROVED, BOOKING_BOOKED, BOOKING_CANCELLED, BOOKING_CANCELLED_HALF_REFUND, BOOKING_CANCELLED_FULL_REFUND, = range(0, 6)
BOOKING_STATES = [
    (BOOKING_INFO_COMPLETE, 'Information complete'),
    (BOOKING_APPROVED, 'Manually approved'),
    (BOOKING_BOOKED, 'Booked'),
    (BOOKING_CANCELLED, 'Cancelled - deposit kept'),
    (BOOKING_CANCELLED_HALF_REFUND, 'Cancelled - half refund (pre 2015 only)'),
    (BOOKING_CANCELLED_FULL_REFUND, 'Cancelled - full refund'),
]

MANUAL_PAYMENT_CHEQUE, MANUAL_PAYMENT_CASH, MANUAL_PAYMENT_ECHEQUE, MANUAL_PAYMENT_BACS = range(0, 4)

MANUAL_PAYMENT_CHOICES = [
    (MANUAL_PAYMENT_CHEQUE, "Cheque"),
    (MANUAL_PAYMENT_CASH, "Cash"),
    (MANUAL_PAYMENT_ECHEQUE, "e-Cheque"),
    (MANUAL_PAYMENT_BACS, "Bank transfer"),
]


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


class Price(models.Model):
    year = models.PositiveSmallIntegerField()
    price_type = models.PositiveSmallIntegerField(choices=VALUED_PRICE_TYPES)
    price = models.DecimalField(decimal_places=2, max_digits=10)

    class Meta:
        unique_together = [('year', 'price_type')]

    def __str__(self):
        return "%s %s - %s" % (self.get_price_type_display(), self.year, self.price)

    @classmethod
    def get_deposit_prices(cls, years=None):
        q = Price.objects.filter(price_type=PRICE_DEPOSIT)
        if years is not None:
            q = q.filter(year__in=set(years))
        return {p.year: p.price for p in q}


class BookingAccountQuerySet(models.QuerySet):

    def addresses_migrated(self):
        return self.exclude(address_line1="")

    def addresses_not_migrated(self):
        return self.filter(Q(address_line1="") & ~Q(address=""))


class BookingAccountManagerBase(models.Manager):
    def payments_due(self):
        """
        Returns a list of accounts that owe money.
        Account objects are annotated with attribute 'balance_due' as a Decimal
        """
        # To limit the size of queries, so do a SQL query for people who might
        # owe money.
        potentials = (
            self.get_queryset()
            .only('id', 'total_received')
            .annotate(total_amount_due=models.Sum('bookings__amount_due'))
            .exclude(total_amount_due=models.F('total_received'))
        )
        retval = []
        for account in potentials:
            balance_due = account.get_balance(confirmed_only=True,
                                              allow_deposits=True)
            if balance_due > 0:
                account.balance_due = balance_due
                retval.append(account)
        return retval


BookingAccountManager = BookingAccountManagerBase.from_queryset(BookingAccountQuerySet)


def migrate_address(*fields):
    class MigrateAddressMixin(object):
        def save(self, **kwargs):
            for address_field_attr in fields:
                address = getattr(self, address_field_attr)
                if address_field_attr.endswith("_address"):
                    # e.g. contact_address -> contact_line1, gp_address -> gp_line1
                    line1_attr = address_field_attr.replace("_address", "") + "_line1"
                else:
                    # e.g. address
                    line1_attr = address_field_attr + "_line1"

                line1 = getattr(self, line1_attr)
                if address != "" and line1 != "":
                    # They filled the new data in, we can delete the old
                    setattr(self, address_field_attr, "")

            return super(MigrateAddressMixin, self).save(**kwargs)

    return MigrateAddressMixin


class BookingAccount(migrate_address('address'), models.Model):
    # For online bookings, email is required, but not for paper. Initially for online
    # process only email is filled in, so to ensure we can edit all BookingAccounts
    # in the admin, all the address fields have 'blank=True'.
    # We have email with null=True so that we can have unique=True on that field.
    email = models.EmailField(blank=True, unique=True, null=True)
    name = models.CharField(blank=True, max_length=100)
    address = models.TextField(blank=True, help_text="deprecated")
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
    email_communication = models.BooleanField("Receive all communication from CCIW by email where possible", blank=True, default=True)
    subscribe_to_newsletter = models.BooleanField("Subscribe to email newsletter", default=False)
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

    def get_balance(self, confirmed_only=False, allow_deposits=False, deposit_price_dict=None):
        """
        Gets the balance to pay on the account.
        If confirmed_only=True, then only bookings that are confirmed
        (no expiration date) are included as 'received goods'.
        If allow_deposits=True, then bookings that only require deposits
        at this point in time will only count for the deposit amount.

        As an optimisation, a dictionary {year:price in GBP} can be passed in deposit_price_dict.
        """
        today = date.today()
        # If allow_deposits, we only do the sum over bookings that require full
        # amount, then get the required deposit amounts in a separate step.

        # bookings_list and use of _prefetched_objects_cache is necessary to
        # support the booking_secretary_reports view. The two code paths should
        # be equivalent, and must be kept in sync. This also propagates into
        # BookingManager.payable and BookingManager.only_deposit_required.

        if hasattr(self, '_prefetched_objects_cache') and 'bookings' in self._prefetched_objects_cache:
            bookings_list = self._prefetched_objects_cache['bookings']
        else:
            bookings_list = None

        if bookings_list is not None:
            total = Decimal('0.00')
            l = BookingManager.payable(self.bookings, confirmed_only, allow_deposits, today=today,
                                       from_list=bookings_list)
            assert type(l) == list
            for item in l:
                total += item.amount_due

        else:
            total = self.bookings.payable(confirmed_only, allow_deposits, today=today).aggregate(models.Sum('amount_due'))['amount_due__sum']
        if total is None:
            total = Decimal('0.00')

        if allow_deposits:
            # Need to add in the cost of deposits.
            if bookings_list is not None:
                extra_bookings = BookingManager.only_deposit_required(self.bookings, confirmed_only,
                                                                      today=today,
                                                                      from_list=bookings_list)
            else:
                extra_bookings = list(self.bookings.only_deposit_required(confirmed_only, today=today))
            # Need to use the deposit price for each.
            if deposit_price_dict is None:
                deposit_price_dict = Price.get_deposit_prices([b.camp.year for b in extra_bookings])
            for b in extra_bookings:
                p = deposit_price_dict[b.camp.year]
                if p < b.amount_due:
                    total += p
                else:
                    total += b.amount_due

        return total - self.total_received

    def admin_balance(self):
        return self.get_balance(confirmed_only=False, allow_deposits=False)
    admin_balance.short_description = 'balance'
    admin_balance = property(admin_balance)

    def receive_payment(self, amount):
        """
        Adds the amount to the account's total_received field.  This should only
        ever be called by the 'process_payments' management command. Client code
        should use the 'send_payment' function.
        """
        # See process_payments management command for an explanation of the above

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
        # In order to distribute funds, need to take into account the total
        # amount in the account that is not covered by confirmed places
        existing_balance = self.get_balance(confirmed_only=True, allow_deposits=True)
        # The 'pot' is the amount we have as excess and can use to mark places
        # as confirmed.
        pot = -existing_balance
        # Order by booking_expires ascending i.e. earliest first
        candidate_bookings = list(self.bookings.unconfirmed()
                                  .order_by('booking_expires')
                                  .prefetch_related('camp')
                                  )
        i = 0
        confirmed_bookings = []
        while pot > 0 and i < len(candidate_bookings):
            b = candidate_bookings[i]
            amount = b.amount_now_due()
            if amount <= pot:
                b.confirm()
                b.save()
                confirmed_bookings.append(b)
                pot -= amount
            i += 1
        if confirmed_bookings:
            places_confirmed.send(self, bookings=confirmed_bookings, payment_received=True)

    def get_address_display(self):
        if self.address_line1:
            return "\n".join(v for v in [self.address_line1,
                                         self.address_line2,
                                         self.address_city,
                                         self.address_county,
                                         self.address_country.code if self.address_country else None,
                                         ] if v)
        else:
            return self.address


class BookingQuerySet(models.QuerySet):

    def for_year(self, year):
        return self.filter(camp__year__exact=year)

    def in_basket(self):
        return self._ready_to_book(False)

    def on_shelf(self):
        return self._ready_to_book(True)

    def _ready_to_book(self, shelved):
        qs = self.filter(shelved=shelved)
        return qs.filter(state=BOOKING_INFO_COMPLETE) | qs.filter(state=BOOKING_APPROVED)

    def booked(self):
        return self.filter(state=BOOKING_BOOKED)

    def in_basket_or_booked(self):
        return self.in_basket() | self.booked()

    def confirmed(self):
        return self.filter(state=BOOKING_BOOKED,
                           booking_expires__isnull=True)

    def unconfirmed(self):
        return self.filter(state=BOOKING_BOOKED,
                           booking_expires__isnull=False)

    def payable(self, confirmed_only, full_amount_only, today=None, from_list=None):
        """
        Returns bookings for which payment is due.
        If confirmed_only is True, unconfirmed places are excluded.
        If full_amount_only is True, places which require only the deposit
        at this point in time are excluded.
        """
        # 'Full refund' cancelled bookings do not have payment due, but the
        # others do.
        # Logic duplicated in booking_secretary_reports.
        if full_amount_only:
            if today is None:
                today = date.today()
            cutoff = today + timedelta(days=settings.BOOKING_FULL_PAYMENT_DUE_DAYS)

        # Optimization - duplicates the logic below
        if from_list is not None:
            bookings = from_list
            retval = [b for b in bookings if b.state in [BOOKING_CANCELLED, BOOKING_CANCELLED_HALF_REFUND]]
            if confirmed_only:
                retval = retval + [b for b in bookings if b.is_confirmed]
            else:
                retval = retval + [b for b in bookings if b.is_booked]

            if full_amount_only:
                retval = [b for b in retval if not (b.camp.start_date > cutoff)]

            return retval

        cancelled = self.filter(state__in=[BOOKING_CANCELLED,
                                           BOOKING_CANCELLED_HALF_REFUND])
        retval = cancelled | (self.confirmed() if confirmed_only else self.booked())
        if full_amount_only:
            retval = retval.exclude(camp__start_date__gt=cutoff)
        return retval

    def only_deposit_required(self, confirmed_only, today=None, from_list=None):
        if today is None:
            today = date.today()
        cutoff = today + timedelta(days=settings.BOOKING_FULL_PAYMENT_DUE_DAYS)

        retval = self.payable(confirmed_only, False, today=today, from_list=from_list)
        if isinstance(retval, list):
            return [b for b in retval if b.camp.start_date > cutoff]
        else:
            return retval.filter(camp__start_date__gt=cutoff)

    def cancelled(self):
        return self.filter(state__in=[BOOKING_CANCELLED,
                                      BOOKING_CANCELLED_HALF_REFUND,
                                      BOOKING_CANCELLED_FULL_REFUND])

    def need_approving(self):
        # See also Booking.approval_reasons()
        qs = self.filter(state=BOOKING_INFO_COMPLETE).select_related('camp')
        qs_custom_price = qs.filter(price_type=PRICE_CUSTOM)
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

    def _address_migrated_q(self):
        return Q(address_line1="") | Q(contact_line1="") | Q(gp_line1="")

    def addresses_migrated(self):
        return self.exclude(self._address_migrated_q())

    def addresses_not_migrated(self):
        return self.filter(self._address_migrated_q())


class BookingManagerBase(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(BookingManagerBase, self).get_queryset().select_related('camp', 'account')

    def most_recent_booking_year(self):
        b = self.get_queryset().booked().order_by('-camp__year').select_related('camp').first()
        if b:
            return b.camp.year
        else:
            return None


BookingManager = BookingManagerBase.from_queryset(BookingQuerySet)


class Booking(migrate_address('address', 'contact_address', 'gp_address'),
              models.Model):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='bookings')

    # Booking details - from user
    camp = models.ForeignKey(Camp,
                             on_delete=models.CASCADE,
                             related_name='bookings')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=SEXES)
    date_of_birth = models.DateField()
    address = models.TextField(blank=True, help_text="deprecated")
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
    contact_address = models.TextField(blank=True, help_text="deprecated")
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
    gp_address = models.TextField("GP address", blank=True, help_text="deprecated")
    gp_line1 = models.CharField("address line 1", max_length=255)
    gp_line2 = models.CharField("address line 2", max_length=255, blank=True)
    gp_city = models.CharField("town/city", max_length=255)
    gp_county = models.CharField("county/state", max_length=255, blank=True)
    gp_country = CountryField("country", null=True)
    gp_post_code = models.CharField("post code", max_length=10)
    gp_phone_number = models.CharField("GP phone number", max_length=22)

    # Medical details - from user
    medical_card_number = models.CharField("NHS number", max_length=100)  # no idea how long it should be
    last_tetanus_injection = models.DateField(null=True, blank=True)
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
    price_type = models.PositiveSmallIntegerField(choices=BOOKING_PLACE_PRICE_TYPES)
    early_bird_discount = models.BooleanField(default=False, help_text="Online bookings only")
    booked_at = models.DateTimeField(null=True, blank=True, help_text="Online bookings only")
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - user driven
    shelved = models.BooleanField(default=False,
                                  help_text="Used by user to put on 'shelf'")

    # State - internal
    state = models.IntegerField(choices=BOOKING_STATES,
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

    # Methods

    def __str__(self):
        return "%s, %s, %s" % (self.name, self.camp.slug_name_with_year,
                               self.account)

    @property
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)

    # Main business rules here
    @property
    def is_booked(self):
        return self.state == BOOKING_BOOKED

    @property
    def is_confirmed(self):
        return self.is_booked and self.booking_expires is None

    def expected_amount_due(self):
        if self.price_type == PRICE_CUSTOM:
            return None
        if self.state == BOOKING_CANCELLED:
            return Price.objects.get(year=self.camp.year,
                                     price_type=PRICE_DEPOSIT).price
        elif self.state == BOOKING_CANCELLED_FULL_REFUND:
            return Decimal('0.00')
        else:
            amount = Price.objects.get(year=self.camp.year,
                                       price_type=self.price_type).price
            # For booking 2015 and later, this is not needed, but it kept in
            # case we need to query the expected amount due for older bookings.
            if self.south_wales_transport:
                amount += Price.objects.get(price_type=PRICE_SOUTH_WALES_TRANSPORT,
                                            year=self.camp.year).price

            if self.early_bird_discount:
                amount -= Price.objects.get(price_type=PRICE_EARLY_BIRD_DISCOUNT,
                                            year=self.camp.year).price

            # For booking 2015 and later, there are no half refunds,
            # but this is kept in in case we need to query the expected amount due for older
            # bookings.
            if self.state == BOOKING_CANCELLED_HALF_REFUND:
                amount = amount / 2

            return amount

    def auto_set_amount_due(self):
        if self.price_type == PRICE_CUSTOM:
            if self.amount_due is None:
                self.amount_due = Decimal('0.00')
            # Otherwise do nothing - we can't auto set for a custom amount
        else:
            self.amount_due = self.expected_amount_due()

    def amount_now_due(self):
        # Amount due, taking into account the fact that only a deposit might be due.
        cutoff = date.today() + timedelta(days=settings.BOOKING_FULL_PAYMENT_DUE_DAYS)
        if self.camp.start_date > cutoff:
            p = Price.objects.get(price_type=PRICE_DEPOSIT, year=self.camp.year).price
            if p < self.amount_due:
                return p
        return self.amount_due

    def can_have_early_bird_discount(self, booked_at=None):
        if booked_at is None:
            booked_at = self.booked_at
        if self.price_type == PRICE_CUSTOM:
            return False
        else:
            return early_bird_is_available(self.camp.year, booked_at)

    def early_bird_discount_missed(self):
        """
        Returns the discount that was missed due to failing to book early.
        """
        if self.early_bird_discount or self.price_type == PRICE_CUSTOM:
            return Decimal(0)  # Got the discount, or it wasn't available.
        return Price.objects.get(price_type=PRICE_EARLY_BIRD_DISCOUNT,
                                 year=self.camp.year).price

    def age_on_camp(self):
        # Age is calculated based on school years, i.e. age on 31st August
        # See also BookingManager.need_approving()
        return relativedelta(self.age_base_date(), self.date_of_birth).years

    def age_base_date(self):
        return date(self.camp.year, 8, 31)

    @property
    def is_too_young(self):
        return self.age_on_camp() < self.camp.minimum_age

    @property
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
        if self.is_custom_discount:
            reasons.append("Custom discount")
        if self.is_too_young:
            reasons.append("Too young")
        if self.is_too_old:
            reasons.append("Too old")
        return reasons

    def get_available_discounts(self, now):
        retval = []
        if self.can_have_early_bird_discount(booked_at=now):
            retval.append(("Early bird discount if booked now",
                           Price.objects.get(year=self.camp.year,
                                             price_type=PRICE_EARLY_BIRD_DISCOUNT).price))
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
        if self.state == BOOKING_APPROVED and not booking_sec:
            return ([], [])

        return (self.get_booking_errors(booking_sec=booking_sec),
                self.get_booking_warnings(booking_sec=booking_sec))

    def get_booking_errors(self, booking_sec=False):
        errors = []

        # Custom price - not auto bookable
        if self.price_type == PRICE_CUSTOM:
            errors.append("A custom discount needs to be arranged by the booking secretary")

        relevant_bookings = self.account.bookings.for_year(self.camp.year).in_basket_or_booked()
        relevant_bookings_excluding_self = relevant_bookings.exclude(first_name=self.first_name,
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

        if self.price_type == PRICE_2ND_CHILD:
            if not (relevant_bookings_excluding_self
                    .filter(price_type=PRICE_FULL)
                    ).exists():
                errors.append("You cannot use a 2nd child discount unless you have "
                              "another child at full price. Please edit the place details "
                              "and choose an appropriate price type.")

        if self.price_type == PRICE_3RD_CHILD:
            qs = (relevant_bookings_excluding_self.filter(price_type=PRICE_FULL) |
                  relevant_bookings_excluding_self.filter(price_type=PRICE_2ND_CHILD))
            if qs.count() < 2:
                errors.append("You cannot use a 3rd child discount unless you have "
                              "two other children without this discount. Please edit the "
                              "place details and choose an appropriate price type.")

        if self.price_type in [PRICE_2ND_CHILD, PRICE_3RD_CHILD]:
            qs = relevant_bookings.filter(first_name=self.first_name,
                                          last_name=self.last_name)
            qs = qs.filter(price_type=PRICE_2ND_CHILD) | qs.filter(price_type=PRICE_3RD_CHILD)
            if qs.count() > 1:
                errors.append("If a camper goes on multiple camps, only one place may use a 2nd/3rd child discount.")

        # serious illness
        if self.serious_illness:
            errors.append("Must be approved by leader due to serious illness/condition")

        # Check age.
        camper_age = self.age_on_camp()
        age_base = self.age_base_date().strftime("%e %B %Y")
        if self.is_too_young:
            errors.append("Camper will be %d which is below the minimum age (%d) on %s"
                          % (camper_age, self.camp.minimum_age, age_base))

        if self.is_too_old:
            errors.append("Camper will be %d which is above the maximum age (%d) on %s"
                          % (camper_age, self.camp.maximum_age, age_base))

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

        if places_available and self.sex == SEX_MALE:
            if places_left_male <= 0:
                errors.append("There are no places left for boys on this camp.")
                places_available = False

        if places_available and self.sex == SEX_FEMALE:
            if places_left_female <= 0:
                errors.append("There are no places left for girls on this camp.")
                places_available = False

        if places_available:
            # Complex - need to check the other places that are about to be booked.
            # (if there is one place left, and two campers for it, we can't say that
            # there are enough places)
            same_camp_bookings = self.account.bookings.filter(camp=self.camp).in_basket()
            places_to_be_booked = same_camp_bookings.count()
            places_to_be_booked_male = same_camp_bookings.filter(sex=SEX_MALE).count()
            places_to_be_booked_female = same_camp_bookings.filter(sex=SEX_FEMALE).count()

            if places_left < places_to_be_booked:
                errors.append("There are not enough places left on this camp "
                              "for the campers in this set of bookings.")
                places_available = False

            if places_available and self.sex == SEX_MALE:
                if places_left_male < places_to_be_booked_male:
                    errors.append("There are not enough places for boys left on this camp "
                                  "for the campers in this set of bookings.")
                    places_available = False

            if places_available and self.sex == SEX_FEMALE:
                if places_left_female < places_to_be_booked_female:
                    errors.append("There are not enough places for girls left on this camp "
                                  "for the campers in this set of bookings.")
                    places_available = False

        if self.south_wales_transport and not self.camp.south_wales_transport_available:
            errors.append("Transport from South Wales is not available for this camp, or all places have been taken already.")

        if booking_sec and self.price_type != PRICE_CUSTOM:
            expected_amount = self.expected_amount_due()
            if self.amount_due != expected_amount:
                errors.append("The 'amount due' is not the expected value of £%s." % expected_amount)

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
            warnings.append("You have entered another set of place details for a camper "
                            "called '%s' on camp %s. Please ensure you don't book multiple "
                            "places for the same camper!" % (self.name, self.camp.name))

        relevant_bookings = self.account.bookings.for_year(self.camp.year).in_basket_or_booked()

        if self.price_type == PRICE_FULL:
            full_pricers = relevant_bookings.filter(price_type=PRICE_FULL)
            names = sorted(set([b.name for b in full_pricers]))
            if len(names) > 1:
                pretty_names = ', '.join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at 'Full price'. "
                if len(names) == 2:
                    warning += ("If %s are from the same family, one is eligible "
                                "for the 2nd child discount." % pretty_names)
                else:
                    warning += ("If %s are from the same family, one or more is eligible "
                                "for the 2nd or 3rd child discounts." % pretty_names)

                warnings.append(warning)

        if self.price_type == PRICE_2ND_CHILD:
            second_childers = relevant_bookings.filter(price_type=PRICE_2ND_CHILD)
            names = sorted(set([b.name for b in second_childers]))
            if len(names) > 1:
                pretty_names = ', '.join(names[1:]) + " and " + names[0]
                warning = "You have multiple places at '2nd child discount'. "
                if len(names) == 2:
                    warning += ("If %s are from the same family, one is eligible "
                                "for the 3rd child discount." % pretty_names)
                else:
                    warning += ("If %s are from the same family, %d are eligible "
                                "for the 3rd child discount." % (pretty_names,
                                                                 len(names) - 1))

                warnings.append(warning)

        return warnings

    def confirm(self):
        self.booking_expires = None

    def expire(self):
        self.booking_expires = None
        self.state = BOOKING_INFO_COMPLETE
        self.early_bird_discount = False
        self.booked_at = None
        self.auto_set_amount_due()

    def is_user_editable(self):
        return self.state == BOOKING_INFO_COMPLETE

    @property
    def is_custom_discount(self):
        return self.price_type == PRICE_CUSTOM

    def get_contact_email(self):
        if self.email:
            return self.email
        elif self.account_id is not None:
            return self.account.email

    def get_address_display(self):
        if self.address_line1:
            return "\n".join(v for v in [self.address_line1,
                                         self.address_line2,
                                         self.address_city,
                                         self.address_county,
                                         self.address_country.code if self.address_country else None,
                                         self.address_post_code,
                                         ] if v)
        else:
            return self.address

    def get_contact_address_display(self):
        if self.contact_line1:
            return "\n".join(v for v in [self.contact_name,
                                         self.contact_line1,
                                         self.contact_line2,
                                         self.contact_city,
                                         self.contact_county,
                                         self.contact_country.code if self.contact_country else None,
                                         self.contact_post_code,
                                         ] if v)
        else:
            return self.contact_address

    def get_gp_address_display(self):
        if self.gp_line1:
            return "\n".join(v for v in [self.gp_line1,
                                         self.gp_line2,
                                         self.gp_city,
                                         self.gp_county,
                                         self.gp_country.code if self.gp_country else None,
                                         self.gp_post_code,
                                         ] if v)
        else:
            return self.gp_address

    class Meta:
        ordering = ['-created']


def book_basket_now(bookings):
    """
    Book a basket of bookings, returning True if successful,
    False otherwise.
    """
    try:
        lock = Lock(os.path.join(os.environ['HOME'], '.cciw_booking_lock'))
        lock.acquire()
        bookings = list(bookings)
        now = timezone.now()
        for b in bookings:
            if len(b.get_booking_problems()[0]) > 0:
                return False

        for b in bookings:
            b.booked_at = now
            # Early bird discounts are only applied for online bookings, and
            # this needs to be re-assessed if a booking expires and is later
            # booked again. Therefore it makes sense to put the logic here
            # rather than in the Booking model.
            b.early_bird_discount = b.can_have_early_bird_discount()
            b.auto_set_amount_due()
            b.state = BOOKING_BOOKED
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
    finally:
        lock.release()


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
    return (Price.objects.filter(year=year, price_type__in=[v for v, d in REQUIRED_PRICE_TYPES]).count()
            == len(REQUIRED_PRICE_TYPES)
            and Camp.objects.filter(year=year).exists())

is_booking_open_thisyear = lambda: is_booking_open(common.get_thisyear())


# See process_payments management command for explanation

class PaymentManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(PaymentManager, self).get_queryset().select_related('account')


class Payment(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    account = models.ForeignKey(BookingAccount,
                                related_name='payments',
                                on_delete=models.CASCADE)
    origin_id = models.PositiveIntegerField()
    origin_type = models.ForeignKey(ContentType,
                                    on_delete=models.PROTECT)
    origin = GenericForeignKey('origin_type', 'origin_id')
    processed = models.DateTimeField(null=True)
    created = models.DateTimeField()

    objects = PaymentManager()

    def __str__(self):
        if self.origin is not None and hasattr(self.origin, 'payment_description'):
            retval = self.origin.payment_description
        else:
            retval = "Payment: %s %s %s via %s" % (abs(self.amount),
                                                   'from' if self.amount > 0 else 'to',
                                                   self.account.name, self.origin_type)
            if self.origin is None:
                retval += " (deleted)"

        return retval

    def payment_type(self):
        if hasattr(self.origin, 'get_payment_type_display'):
            return self.origin.get_payment_type_display()
        else:
            return "PayPal"


class ManualPaymentManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(ManualPaymentManager, self).get_queryset().select_related('account')


class ManualPaymentBase(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created = models.DateTimeField(default=timezone.now)
    payment_type = models.PositiveSmallIntegerField(choices=MANUAL_PAYMENT_CHOICES,
                                                    default=MANUAL_PAYMENT_CHEQUE)

    objects = ManualPaymentManager()

    class Meta:
        abstract = True


class ManualPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='manual_payments')

    def __str__(self):
        return "Manual payment of £%s from %s" % (self.amount, self.account)


class RefundPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount,
                                on_delete=models.CASCADE,
                                related_name='refund_payments')

    def __str__(self):
        return "Refund payment of £%s to %s" % (self.amount, self.account)


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


def trigger_payment_processing():
    # NB - this is always called from a web request, for which the virtualenv
    # has been set up in os.environ, so this is passed on and the correct python
    # runs manage.py.
    if settings.TESTS_RUNNING:
        process_all_payments()
    else:
        manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
        os.spawnl(os.P_NOWAIT, manage_py, 'manage.py', 'process_payments')


def send_payment(amount, to_account, from_obj):
    Payment.objects.create(amount=amount,
                           account=to_account,
                           origin=from_obj,
                           processed=None,
                           created=timezone.now())
    trigger_payment_processing()


# These are called normally from process_payments management command.

@transaction.atomic
def process_one_payment(payment):
    payment.account.receive_payment(payment.amount)
    payment.processed = timezone.now()
    # Can't save Payment, so do update
    Payment.objects.filter(id=payment.id).update(processed=payment.processed)


def process_all_payments():
    for payment in Payment.objects.filter(processed__isnull=True).order_by('created'):
        try:
            process_one_payment(payment)
        except Exception:
            # Send email, but carry on with next payment
            from cciw.cciwmain.common import exception_notify_admins
            try:
                exception_notify_admins('CCIW booking - payment processing error')
            except Exception:
                # Exception sending email - that's the most likely cause
                # of process_one_payment failing, since it can
                # indirectly cause email to be sent. In that case, the
                # admin notification is likely to fail too.
                continue


from .hooks import *  # NOQA isort:skip
