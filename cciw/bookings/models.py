from datetime import datetime

from django.db import models

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
    (PRICE_CUSTOM,    'Custom'),
]

BOOKING_STARTED, BOOKING_INFO_COMPLETE, BOOKING_APPROVED, BOOKING_BOOKED, BOOKING_EXPIRED = range(0, 5)
BOOKING_STATES = [
    (BOOKING_STARTED, 'Started'),
    (BOOKING_INFO_COMPLETE, 'Information complete'),
    (BOOKING_APPROVED, 'Manually approved'),
    (BOOKING_BOOKED, 'Booked'),
    (BOOKING_EXPIRED, 'Place booking expired'),
]

class BookingAccount(models.Model):
    # For online bookings, email is required, but not for paper. Initially for online
    # process only email is filled in, so to ensure we can edit all BookingAccounts
    # in the admin, all the address fields have 'blank=True'.
    email = models.EmailField(blank=True, unique=True)
    name = models.CharField(blank=True, max_length=100)
    address = models.TextField(blank=True)
    post_code = models.CharField(blank=True, max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    share_phone_number = models.BooleanField(blank=True, default=False)
    total_received = models.DecimalField(decimal_places=2, max_digits=10)
    activated = models.DateField(null=True)


class Booking(models.Model):
    account = models.ForeignKey(BookingAccount)

    # Booking details - from user
    camp = models.ForeignKey(Camp)
    name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=SEXES)
    date_of_birth = models.DateField()
    address = models.TextField()
    post_code = models.CharField(max_length=10)
    phone_number = models.CharField(blank=True, max_length=22)
    church = models.CharField("name of church", max_length=100)
    south_wales_transport = models.BooleanField("requires transport from South Wales",
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
    last_tetanus_injection = models.DateField(null=True)
    allergies = models.TextField(blank=True)
    regular_medication_required = models.TextField(blank=True)
    illnesses = models.TextField(blank=True)
    learning_difficulties = models.TextField(blank=True)
    serious_illness = models.BooleanField(blank=True, default=False)

    # Agreement - from user
    agreement = models.BooleanField(default=False, blank=False)
    agreement_date = models.DateField()

    # Price - partly from user (must fit business rules)
    price_type = models.IntegerField(choices=PRICE_TYPES)
    amount_due = models.DecimalField(decimal_places=2, max_digits=10)

    # State - internal
    state = models.IntegerField(choices=BOOKING_STATES)
    created = models.DateField(default=datetime.now)
    booking_expires = models.DateField(null=True)

