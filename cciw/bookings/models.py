from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import re

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils.safestring import mark_safe

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import Lock

# = Business rules =
#
# Business rules are implemented in relevant models and managers.
#
#



SEX_MALE, SEX_FEMALE = 'm', 'f'
SEXES = [
    (SEX_MALE, 'Male'),
    (SEX_FEMALE, 'Female'),
]

PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, PRICE_SOUTH_WALES_TRANSPORT = range(0, 5)
PRICE_TYPES = [
    (PRICE_FULL,      'Full price'),
    (PRICE_2ND_CHILD, '2nd child discount'),
    (PRICE_3RD_CHILD, '3rd child discount'),
    (PRICE_CUSTOM,    'Custom discount'),
]

# Price types that are used by Price model
VALUED_PRICE_TYPES = [(v,d) for (v,d) in PRICE_TYPES if v is not PRICE_CUSTOM] + \
    [(PRICE_SOUTH_WALES_TRANSPORT, 'South wales transport surcharge')]


BOOKING_INFO_COMPLETE, BOOKING_APPROVED, BOOKING_BOOKED = range(0, 3)
BOOKING_STATES = [
    (BOOKING_INFO_COMPLETE, 'Information complete'),
    (BOOKING_APPROVED, 'Manually approved'),
    (BOOKING_BOOKED, 'Booked'),
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

    # Business methods:

    def get_balance(self, confirmed_only=False):
        """
        Gets the balance to pay on the account.
        If confirmed_only=True, then only bookings that are confirmed
        (no expiration date) are included as 'received goods'
        """
        if confirmed_only:
            total = self.bookings.confirmed().aggregate(models.Sum('amount_due'))['amount_due__sum']

        else:
            total = self.bookings.booked().aggregate(models.Sum('amount_due'))['amount_due__sum']
        if total is None:
            total = Decimal('0.00')
        return total - self.total_received

    def receive_payment(self, amount):
        # = Receiving payments =
        #
        # This system needs to be robust, and cope with all kinds of user error, and
        # things not matching up. The essential philosophy of this code is to assume the
        # worst, most complicated scenario, and this will then easily handle the more
        # simple case where everything matches up as a special case.
        #
        # When a payment is received, django-paypal creates an object
        # and a signal handler calls BookingAccount.receive_payment, which must
        # update the 'total_received' field.
        #
        # We also need to set the 'Booking.booking_expires' field of relevant Booking
        # objects to null, so that the place is securely booked.
        #
        # There are a number of scenarios where the amount paid doesn't cover the total
        # amount due:
        # 1) user fiddles with the form client side and alters the amount
        # 2) user starts paying for one place, then books another place in a different
        # tab/window
        #
        # It is also possible for a place to be partially paid for, yet booked e.g. if a
        # user selects a discount for which they were not eligible, and pays. This is then
        # discovered, and the 'amount due' for that place is altered by an admin.
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
        existing_balance = self.get_balance(confirmed_only=True)
        # The 'pot' is the amount we have as excess and can use to mark places
        # as confirmed.
        pot = -existing_balance
        # Order by booking_expires ascending i.e. earliest first
        candidate_bookings = list(self.bookings.unconfirmed()
                                  .order_by('booking_expires'))
        i = 0
        while pot > 0 and i < len(candidate_bookings):
            b = candidate_bookings[i]
            if b.amount_due <= pot:
                b.confirm()
                b.save()
                pot -= b.amount_due
            i += 1


class BookingManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        return super(BookingManager, self).get_query_set().select_related('camp', 'account')

    def basket(self, year):
        return self._ready_to_book(year, False)

    def shelf(self, year):
        return self._ready_to_book(year, True)

    def _ready_to_book(self, year, shelved):
        qs = self.get_query_set().filter(camp__year__exact=year, shelved=shelved)
        return qs.filter(state=BOOKING_INFO_COMPLETE) | qs.filter(state=BOOKING_APPROVED)

    def booked(self):
        return self.get_query_set().filter(state=BOOKING_BOOKED)

    def confirmed(self):
        return self.get_query_set().filter(state=BOOKING_BOOKED,
                                           booking_expires__isnull=True)

    def unconfirmed(self):
        return self.get_query_set().filter(state=BOOKING_BOOKED,
                                           booking_expires__isnull=False)


class Booking(models.Model):
    account = models.ForeignKey(BookingAccount, related_name='bookings')

    # Booking details - from user
    camp = models.ForeignKey(Camp, related_name='bookings')
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

    # State - user driven
    shelved = models.BooleanField(default=False)

    # State - internal
    state = models.IntegerField(choices=BOOKING_STATES,
                                help_text=mark_safe(
            "<ul><li>Move to 'Manually approved' to allow user to book and pay</li>"
            "<li>To book, move to 'Booked' <b>and</b> ensure 'Booking expires' is empty</li>"
            "</ul>"))

    created = models.DateTimeField(default=datetime.now)
    booking_expires = models.DateTimeField(null=True, blank=True)


    objects = BookingManager()

    # Methods

    def __unicode__(self):
        return "%s, %s-%s, %s" % (self.name, self.camp.year, self.camp.number,
                                  self.account)

    ### Main business rules here ###

    def confirmed_booking(self):
        return self.state == BOOKING_BOOKED and self.booking_expires is None
    confirmed_booking.boolean = True

    def auto_set_amount_due(self):
        if self.price_type == PRICE_CUSTOM:
            if self.amount_due is None:
                self.amount_due = Decimal('0.00')
        else:
            amount = Price.objects.get(year=self.camp.year,
                                       price_type=self.price_type).price
            if self.south_wales_transport:
                amount += Price.objects.get(price_type=PRICE_SOUTH_WALES_TRANSPORT,
                                            year=self.camp.year).price
            self.amount_due = amount

    def get_booking_problems(self):
        """
        Returns a two tuple (errors, warnings), where 'errors' is a list of
        reasons why booking cannot be done. If empty list, then it can be.
        'warnings' is a list of possible problems that don't stop booking.
        """
        errors = []
        warnings = []

        if self.state == BOOKING_APPROVED:
            return ([], [])

        # Custom price - not auto bookable
        if self.price_type == PRICE_CUSTOM:
            errors.append("A custom discount needs to be arranged by the booking secretary")

        # 2nd/3rd child discounts
        if self.price_type == PRICE_2ND_CHILD:
            qs = self.account.bookings.filter(shelved=False, camp__year__exact=self.camp.year)
            if not qs.filter(price_type=PRICE_FULL).exists():
                errors.append("You cannot use a 2nd child discount unless you have "
                              "a child at full price. Please edit the place details "
                              "and choose an appropriate price type.")

        if self.price_type == PRICE_3RD_CHILD:
            qs = self.account.bookings.filter(shelved=False, camp__year__exact=self.camp.year)
            qs = qs.filter(price_type=PRICE_FULL) | qs.filter(price_type=PRICE_2ND_CHILD)
            if qs.count() < 2:
                errors.append("You cannot use a 3rd child discount unless you have "
                              "two other places without this discount. Please edit the "
                              "place details and choose an appropriate price type.")

        # serious illness
        if self.serious_illness:
            errors.append("Must be approved by leader due to serious illness/condition")

        # Check age.
        # Age is calculated based on shool years, i.e. age on 31st August
        camper_age = relativedelta(date(self.camp.year, 8, 31), self.date_of_birth)
        if camper_age.years < self.camp.minimum_age:
            errors.append("Camper will be below the minimum age (%d) on the 31st August %d"
                          % (self.camp.minimum_age, self.camp.year))

        if camper_age.years > self.camp.maximum_age:
            errors.append("Camper will be above the maximum age (%d) on the 31st August %d"
                          % (self.camp.maximum_age, self.camp.year))

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
            same_camp_bookings = self.account.bookings.basket(self.camp.year).filter(camp=self.camp)
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

        if self.account.bookings.filter(name=self.name).exclude(id=self.id):
            warnings.append("You have entered another set of place details for a camper "
                            "called '%s' on camp %d. Please ensure you don't book multiple "
                            "places for the same camper!" % (self.name, self.camp.number))

        return (errors, warnings)

    def confirm(self):
        self.booking_expires = None

    def is_user_editable(self):
        return self.state == BOOKING_INFO_COMPLETE

    class Meta:
        ordering = ['-created']


def book_basket_now(bookings):
    try:
        lock = Lock(os.path.join(os.environ['HOME'], '.cciw_booking_lock'))
        lock.acquire()
        bookings = list(bookings)
        now = datetime.now()
        for b in bookings:
            if len(b.get_booking_problems()[0]) > 0:
                return False

        for b in bookings:
            b.state = BOOKING_BOOKED
            b.booking_expires = now + timedelta(1) # 24 hours
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


### Payments ####

def unrecognised_payment(ipn_obj):
    # If an online payment does not reference an existing BookingAccount, we accept it
    # but complain loudly by email.
    pass # TODO


def paypal_payment_received(sender, **kwargs):
    ipn_obj = sender
    m = re.match("account:(\d+);", ipn_obj.custom)
    if m is None:
        unrecognised_payment(ipn_obj)
        return

    try:
        account = BookingAccount.objects.get(id=int(m.groups()[0]))
        account.receive_payment(ipn_obj.mc_gross)
    except BookingAccount.DoesNotExist:
        unrecognised_payment(ipn_obj)


# Payment signals
from paypal.standard.ipn.signals import payment_was_successful
payment_was_successful.connect(paypal_payment_received)
