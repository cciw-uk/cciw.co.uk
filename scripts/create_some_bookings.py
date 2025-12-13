#!/usr/bin/env python

# Script to create some bookings for testing purposes, based on

import itertools
import random
from datetime import date

import django

django.setup()

from django.utils import timezone  # noqa: E402
from faker import Faker  # noqa: E402

from cciw.bookings.models.bookings import Booking  # noqa: E402
from cciw.bookings.models.states import BookingState  # noqa: E402
from cciw.cciwmain.models import Camp  # noqa: E402

faker = Faker("en_GB")


def create(year: int, *, fix_names_from_anonymised: bool):
    previous_year = year - 1
    previous_year_bookings: list[Booking] = list(Booking.objects.for_year(previous_year).booked().order_by("account"))

    if fix_names_from_anonymised:
        # First, update (anonymised) names to re-create sibling groups.

        for group in itertools.groupby(previous_year_bookings, key=lambda b: int(b.account_id)):
            _, bookings = group
            bookings = list(bookings)
            # Assume that more than 4 bookings mean a large group booking that isn't a family.
            if len(bookings) <= 4:
                family_last_name = bookings[0].last_name
                for b in bookings:
                    if b.last_name != family_last_name:
                        b.last_name = family_last_name
                        b.save()

    # Now, make some more
    for b in previous_year_bookings:
        old_id = b.id

        b.id = None  # Create new booking on save. This is a clone basically.
        b.state = BookingState.INFO_COMPLETE
        b.created_at = timezone.now()

        old_camp = b.camp
        new_camp = Camp.objects.get(camp_name=old_camp.camp_name, year=year)
        b.camp = new_camp

        # Remove those who are too old.
        if b.age_on_camp() > new_camp.maximum_age:
            continue

        # Remove some psuedo-randomly to give more spaces:
        if hash(str(old_id) + "a") % 5 == 0:
            continue

        b.save()

        # Create some "younger siblings"
        if hash(str(old_id) + "b") % 3 == 0:
            b.id = None
            b.state = BookingState.INFO_COMPLETE
            b.created_at = timezone.now()
            b.first_name = faker.first_name()
            birth_date_year = new_camp.year - new_camp.minimum_age - 1
            b.birth_date = date(birth_date_year, 2, 1)
            b.save()

    # Make some more, younger ones, with different booking accounts, randomised names.
    # Get some old bookings, which are less likely to interfere in terms of booking accounts.
    old_bookings = Booking.objects.for_year(year=2013).booked()

    for b in old_bookings:
        old_id = b.id

        # Cut most of them:
        if old_id % 3 != 0:
            continue

        b.id = None  # Create new booking on save. This is a clone basically.
        b.state = BookingState.INFO_COMPLETE
        b.created_at = timezone.now()

        old_camp = b.camp
        new_camp = Camp.objects.filter(camp_name=old_camp.camp_name, year=year).first()
        if new_camp is None:
            continue
        b.camp = new_camp

        # Create new names and ages:
        birth_date_max_year = new_camp.year - new_camp.minimum_age - 1
        birth_date_min_year = new_camp.year - new_camp.maximum_age + 1
        birth_date_year = random.choice(list(range(birth_date_min_year, birth_date_max_year + 1)))
        b.first_name = faker.first_name()
        account_surname = b.account.name.split(" ")[-1].title()
        b.last_name = account_surname
        b.birth_date = date(birth_date_year, 2, 1)

        b.save()


def add_to_queue(year: int):
    for booking in Booking.objects.for_year(year):
        booking.add_to_queue()
