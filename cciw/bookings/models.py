from datetime import datetime
from decimal import Decimal

from django.db import models

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp


SEX_MALE, SEX_FEMALE = 'm', 'f'
SEXES = [
    (SEX_MALE, 'Male'),
    (SEX_FEMALE, 'Female'),
]

PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM = range(0, 4)
PRICE_TYPES = [
    (PRICE_FULL,      'Full price'),
    (PRICE_2ND_CHILD, '2nd child discount'),
    (PRICE_3RD_CHILD, '3rd child discount'),
    (PRICE_CUSTOM,    'Custom discount'),
]

# Price types that are used by Price model
VALUED_PRICE_TYPES = [(v,d) for (v,d) in PRICE_TYPES if v is not PRICE_CUSTOM]

BOOKING_STARTED, BOOKING_INFO_COMPLETE, BOOKING_APPROVED, BOOKING_BOOKED, BOOKING_EXPIRED = range(0, 5)
BOOKING_STATES = [
    (BOOKING_STARTED, 'Started'),
    (BOOKING_INFO_COMPLETE, 'Information complete'),
    (BOOKING_APPROVED, 'Manually approved'),
    (BOOKING_BOOKED, 'Booked'),
    (BOOKING_EXPIRED, 'Place booking expired'),
]


class Price(models.Model):
    year = models.PositiveSmallIntegerField()
    price_type = models.PositiveSmallIntegerField(choices=VALUED_PRICE_TYPES)
    price = models.DecimalField(decimal_places=2, max_digits=10)

    class Meta:
        unique_together = ['year', 'price_type']

    def __unicode__(self):
        return u"%s %s - %s" % (self.get_price_type_display(), self.year, self.price)


class BookingAccount(models.Model):
    # For online bookings, email is required, but not for paper. Initially for online
    # process only email is filled in, so to ensure we can edit all BookingAccounts
    # in the admin, all the address fields have 'blank=True'.
    email = models.EmailField(blank=True, unique=True)
    name = models.CharField(blank=True, max_length=100)
    address = models.TextField(blank=True)
    post_code = models.CharField(blank=True, max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    share_phone_number = models.BooleanField("Allow this phone number to be passed on "
                                             "to other parents to help organise transport",
                                             blank=True, default=False)
    total_received = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits=10)
    activated = models.DateTimeField(null=True, blank=True)

    def has_account_details(self):
        return self.name != "" and self.address != "" and self.post_code != ""

    def __unicode__(self):
        out = []
        if self.name:
            out.append(self.name)
        if self.post_code:
            out.append(self.post_code)
        if self.email:
            out.append("<" + self.email + ">")
        if not out:
            out.append("(empty)")
        return u", ".join(out)


class BookingManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        return super(BookingManager, self).get_query_set().select_related('camp', 'account')

    def ready_to_book(self, year):
        qs = self.get_query_set().filter(camp__year__exact=year)
        return qs.filter(state=BOOKING_INFO_COMPLETE) | qs.filter(state=BOOKING_APPROVED)


class Booking(models.Model):
    account = models.ForeignKey(BookingAccount, related_name='bookings')

    # Booking details - from user
    camp = models.ForeignKey(Camp)
    name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=SEXES)
    date_of_birth = models.DateField()
    address = models.TextField()
    post_code = models.CharField(max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    email = models.EmailField(blank=True)
    church = models.CharField("name of church", max_length=100, blank=True)
    south_wales_transport = models.BooleanField("require transport from South Wales",
                                                blank=True, default=False)

    # Contact - from user
    contact_name = models.CharField(max_length=100)
    contact_phone_number = models.CharField(max_length=22)

    # Diet - from user
    dietary_requirements = models.TextField(blank=True)

    # GP details - from user
    gp_name = models.CharField("GP name", max_length=100)
    gp_address = models.TextField("GP address")
    gp_phone_number = models.CharField("GP phone number", max_length=22)

    # Medical details - from user
    medical_card_number = models.CharField(max_length=100) # no idea how long it should be
    last_tetanus_injection = models.DateField(null=True, blank=True)
    allergies = models.TextField(blank=True)
    regular_medication_required = models.TextField(blank=True)
    illnesses = models.TextField(blank=True)
    learning_difficulties = models.TextField(blank=True)
    serious_illness = models.BooleanField(blank=True, default=False)

    # Agreement - from user
    agreement = models.BooleanField(default=False)

    # Price - partly from user (must fit business rules)
    price_type = models.PositiveSmallIntegerField(choices=PRICE_TYPES)
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - internal
    state = models.IntegerField(choices=BOOKING_STATES)
    created = models.DateTimeField(default=datetime.now)
    booking_expires = models.DateTimeField(null=True, blank=True)


    objects = BookingManager()

    # Methods

    def __unicode__(self):
        return "%s, %s-%s, %s" % (self.name, self.camp.year, self.camp.number,
                                  self.account)

    def auto_set_amount_due(self):
        if self.price_type == PRICE_CUSTOM:
            if self.amount_due is None:
                self.amount_due = Decimal('0.00')
        else:
            self.amount_due = Price.objects.get(year=self.camp.year,
                                                price_type=self.price_type).price

    def get_booking_problems(self):
        """
        Returns a list of reasons why booking cannot be done. If empty list,
        then it can be.
        """
        # Main business rules here
        retval = []

        if self.state == BOOKING_APPROVED:
            return retval

        # Custom price - not auto bookable
        if self.price_type == PRICE_CUSTOM:
            retval.append("A custom discount needs to be arranged by the booking secretary")

        # 2nd/3rd child discounts
        if self.price_type == PRICE_2ND_CHILD:
            qs = self.account.bookings.ready_to_book(get_thisyear())
            if not qs.filter(price_type=PRICE_FULL).exists():
                retval.append("You cannot use a 2nd child discount unless you have "
                              "a child at full price.")

        if self.price_type == PRICE_3RD_CHILD:
            qs = self.account.bookings.ready_to_book(get_thisyear())
            qs = qs.filter(price_type=PRICE_FULL) | qs.filter(price_type=PRICE_2ND_CHILD)
            if qs.count() < 2:
                retval.append("You cannot use a 3rd child discount unless you have "
                              "two other places without this discount.")

        # serious illness
        if self.serious_illness:
            retval.append("Must be approved by leader due to serious illness/condition")

        return retval

    class Meta:
        ordering = ['-created']
