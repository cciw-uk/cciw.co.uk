#!/usr/bin/env python
"""Functions to remove sensitive user information

This script is used as a one-off to produce a DB that had realistic
amounts/structure of data but can be shared without problems.

The following rules are to be applied:

- For models with no personally identifying information, the entire model should be kept
  fully intact (ignored). This includes many internal Django models, and many models
  from third party apps.

- For models with personal information:
  - person names are replaced with realistic looking random names.
  - address are replaced with randomised addresses.
  - dates relating to personal information such as date of birth
    are replaced with a date in the same year..
  - other dates are left as they are.
  - sensitive longer text fields are replaced with text of similar size.
  - any potentially sensitive booleans are set to a sensible default.
  - fields that represent internal state or tracking are left as they are.

- For temporary tables that may have sensitive data, such as outgoing email or
  mailer logs, we truncate the table.

In some cases when randomising we put extra effort in to maintain the structure
of existing data, in order to keep realistic data. For example, if the same name
(or other value) is used in a group of related records, we try to replace it
with the same name each time e.g. Bookings from the same BookingAccount over
several years will be given the same 'first_name' and 'last_name'

"""

# ruff: noqa:E402


from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date
from typing import TypeVar

import django

from cciw.data_retention.applying import DELETED_STRING

django.setup()

import tqdm
from django.apps import apps
from django.contrib.admin import models as admin
from django.contrib.auth import models as auth
from django.contrib.contenttypes import models as contenttypes
from django.contrib.sessions import models as sessions
from django.contrib.sites import models as sites
from django.db import models
from faker import Faker

from cciw.accounts import models as accounts
from cciw.accounts.models import (
    BOOKING_SECRETARY_ROLE_NAME,
    DBS_OFFICER_ROLE_NAME,
    User,
)
from cciw.bookings import models as bookings
from cciw.cciwmain import models as cciwmain
from cciw.officers import models as officers
from cciw.sitecontent import models as sitecontent

faker = Faker("en_GB")


# --- Top level ---


def main():
    # test_anonymisation()
    anonymise_db()
    create_users_for_roles()
    print_interesting_people()


def anonymise_db():
    for model, anonymiser in MODEL_HANDLERS.items():
        print(f"Anonymising {model._meta.label}")
        anonymiser.execute()


def create_users_for_roles():
    # This creates some users roles to make it easy to test out specific roles
    for username, is_superuser, role in [
        ("superuser", True, None),
        ("bookingsec", False, BOOKING_SECRETARY_ROLE_NAME),
        ("dbsofficer", False, DBS_OFFICER_ROLE_NAME),
    ]:
        if User.objects.filter(username=username).exists():
            User.objects.filter(username=username).delete()
        user = User(
            username=username,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            is_active=True,
            is_superuser=is_superuser,
            is_staff=True,
            email=f"{username}@example.com",
            contact_phone_number="",
        )
        user.set_password("passwordpassword")
        user.save()
        if role is not None:
            user.roles.set([accounts.Role.objects.get(name=role)])

        print(f"{username} created with {role=}, login using: ?as={username}")
    print()


def print_interesting_people():
    print("Interesting people:")
    last_active_year = bookings.Booking.objects.order_by("-camp__year").first().camp.year
    recent_leaders = [
        user
        for camp in cciwmain.Camp.objects.filter(year=last_active_year)
        for person in camp.leaders.all()
        for user in person.users.all()
    ]
    for user in recent_leaders:
        camp_count = len(user.camps_as_admin_or_leader)
        print(f"  {user.username}  - Camp leader ({camp_count})")


# --- Field Fixers ---

# Functions for changing the value of a field

V = TypeVar("V")  # any value
M = TypeVar("M", bound=models.Model)

type Fixer[M, V] = Callable[[models.Field, M, V], V]


class IgnoreFixerValue:
    # Sentinel for Fixer if return value
    # should not be used.
    pass


# ---- Generic fixers ----


def make_empty(field, instance, value):
    if isinstance(field, models.CharField | models.TextField):
        return ""
    return None


def keep(field, instance, value):
    return value


def similar_length_text(field, instance, value) -> str:
    return value if value == DELETED_STRING else faker.text(max_nb_chars=len(value)) if len(value) > 10 else ""


def same_length_number(field, instance, value) -> str:
    return value if value == DELETED_STRING else faker.numerify("#" * len(value))


def const(constant_val) -> Fixer:
    return lambda field, instance, value: constant_val


def make_birth_date_adult(field, instance, value) -> date:
    return value if value is None else faker.date_of_birth(minimum_age=18)


def make_date_same_year(field, instance, value) -> date:
    return value if value is None else value.replace(month=1, day=1)


# ---- More specific fixers ----


def auto_username(field, user: accounts.User, value):
    num = 0
    while True:
        username = f"{user.first_name}.{user.last_name}".lower()
        if num > 0:
            username = username + str(num)
        if not accounts.User.objects.filter(username=username).exists():
            return username
        num += 1


def dummy_password(field, user: accounts.User, value):
    # Return a password that looks valid, but much much faster
    # than user user.set_password
    return "pbkdf2_sha256$720000$XXXX"


def full_name(f, i, v):
    return f"{faker.first_name()} {faker.last_name()}"


def first_name(f, b, v):
    return faker.first_name()


def last_name(f, b, v):
    return faker.last_name()


def address_line_1(f, i, v):
    return faker.address().split("\n")[0] if v else ""


def city(f, i, v):
    return faker.city() if v else ""


def county(f, i, v):
    return faker.county() if v else ""


def country(f, i, v):
    return faker.country() if v else ""


def post_code(f, i, v):
    return faker.postcode() if v else ""


def phone_number(f, i, v):
    return faker.phone_number() if v else ""


def email_from_name(f, instance, v):
    return f"{instance.name.replace(' ','.')}{abs(hash(v)) % 1000}@example.com"


def mobile_number(f, a, v):
    return faker.cellphone_number() if v else ""


def application_birth_place(f, a, v):
    return faker.city() if v else ""


# --- Anonymisation methods for tables ---


class AllFields:
    pass


class Anonymiser(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def get_fields_covered(self) -> set[str] | AllFields:
        pass


class AnonymiseWithMapAndGroups(Anonymiser):
    # An anonymiser that allows certain fields to be grouped so that
    # equal values in input cols produce equal values in output cols.
    def __init__(self, model: type, field_map: dict[str, Fixer], mapped_field_groups: list[tuple[str]]):
        # mapped_field_groups is a list of tuples of field names.
        # In each tuple of field names, if the value of the set of fields has already been seen
        # and assigned an output, we re-use that value.

        # For example, if mapped_field_groups == [('first_name', 'last_name')]
        # then if we see a specific ('first_name', 'last_name') in the input,
        # then we anonymise it, but the next time we see the same combo
        # we use the same value.

        self.model = model
        self.mapped_field_groups = mapped_field_groups
        self.field_map = field_map

    def execute(self) -> None:
        anonymize_model_with_map_and_groups(self.model, self.field_map, self.mapped_field_groups)

    def get_fields_covered(self) -> set[str]:
        return set(self.field_map.keys())


class AnonymiseWithMap(AnonymiseWithMapAndGroups):
    def __init__(self, model: type, field_map: dict[str, Fixer]):
        super().__init__(model, field_map=field_map, mapped_field_groups=[])


class IgnoreTable(Anonymiser):
    def execute(self):
        # Deliberately do nothing
        pass

    def get_fields_covered(self) -> AllFields:
        return AllFields()


class TruncateTable(Anonymiser):
    def __init__(self, model: type) -> None:
        self.model = model

    def execute(self):
        self.model.objects.all().delete()

    def get_fields_covered(self) -> AllFields:
        return AllFields()


def anonymize_model_with_map_and_groups(
    model: type, field_map: dict[str, Fixer], mapped_field_groups: list[tuple[str]]
):
    # For each group in mapped_field_groups, set up a empty mapping.
    # The inner dict maps from a set (tuple) of old values to a set (tuple) of new values for those fields
    maps: dict[tuple[str], dict[tuple, tuple]] = {k: {} for k in mapped_field_groups}
    all_qs = model.objects.all()
    count = all_qs.count()
    for instance in tqdm.tqdm(all_qs, total=count):
        fields_needed_for_mapped_values = set(attr for attr_group in mapped_field_groups for attr in attr_group)
        saved_field_values = {f: getattr(instance, f) for f in fields_needed_for_mapped_values}

        corrected_fields: set[str] = set()

        # If we already mapped some fields, use mapped values:

        values_to_set: list[tuple[str, object]] = []
        for attr_group in mapped_field_groups:
            mapped_vals = maps[attr_group]
            vals = tuple(getattr(instance, attr) for attr in attr_group)
            if vals in mapped_vals:
                new_vals = mapped_vals[vals]
                for attr, new_val in zip(attr_group, new_vals):
                    if attr not in corrected_fields:
                        # Don't do `setattr` now, or it will stomp on values
                        # that we need to do lookups correctly. Put on a list
                        # to do in a minute
                        values_to_set.append((attr, new_val))
                corrected_fields |= set(attr_group)

        for attr, new_val in values_to_set:
            setattr(instance, attr, new_val)

        # Fix anything not corrected already

        # Note that we go in the order given in field_map, which can be important
        for field_name, fixer in field_map.items():
            field = model._meta.get_field(field_name)
            if field_name in corrected_fields:
                continue
            fixer: Fixer = field_map[field_name]
            value = fixer(field, instance, getattr(instance, field_name))
            if not isinstance(value, IgnoreFixerValue):
                setattr(instance, field_name, value)

        # Save mapped values
        for attr_group in mapped_field_groups:
            old_values = tuple([saved_field_values[attr] for attr in attr_group])
            maps[attr_group][old_values] = tuple(getattr(instance, attr) for attr in attr_group)

        instance.save()


# --- specific models ---


# Bookings:

# Try to keep structure in which the same person is booked year after year,
# from the same booking account.

BOOKINGACCOUNT_FIELD_MAP: dict[str, Fixer[bookings.BookingAccount, object]] = {
    "name": full_name,
    # After name has been changed, make email based on it:
    "email": email_from_name,
    "address_line1": address_line_1,
    "address_line2": make_empty,
    "address_city": city,
    "address_county": county,
    "address_country": country,
    "address_post_code": post_code,
    "phone_number": phone_number,
    "share_phone_number": keep,
    "email_communication": keep,
    "subscribe_to_mailings": keep,
    "subscribe_to_newsletter": keep,
    "total_received": keep,
    "created_at": keep,
    "first_login_at": keep,
    "last_login_at": keep,
    "last_payment_reminder_at": keep,
}

BOOKING_FIELD_MAP: dict[str, Fixer[bookings.Booking, object]] = {
    "first_name": first_name,
    "last_name": last_name,
    "sex": keep,
    "birth_date": make_date_same_year,
    "address_line1": address_line_1,
    "address_line2": make_empty,
    "address_city": city,
    "address_county": county,
    "address_country": country,
    "address_post_code": post_code,
    "phone_number": phone_number,
    "email": email_from_name,
    "church": lambda f, b, v: "Bethel" if v else "",
    "south_wales_transport": keep,
    # Contact
    "contact_name": full_name,
    "contact_line1": address_line_1,
    "contact_line2": make_empty,
    "contact_city": city,
    "contact_county": county,
    "contact_country": country,
    "contact_post_code": post_code,
    "contact_phone_number": phone_number,
    "dietary_requirements": similar_length_text,
    "gp_name": full_name,
    "gp_line1": address_line_1,
    "gp_line2": make_empty,
    "gp_city": city,
    "gp_county": county,
    "gp_country": country,
    "gp_post_code": post_code,
    "gp_phone_number": phone_number,
    "medical_card_number": same_length_number,
    "last_tetanus_injection_date": make_date_same_year,
    "allergies": make_empty,
    "regular_medication_required": keep,
    "illnesses": similar_length_text,
    "can_swim_25m": keep,
    "learning_difficulties": similar_length_text,
    "serious_illness": keep,
    "agreement": keep,
    "publicity_photos_agreement": keep,
    "custom_agreements_checked": keep,
    "price_type": keep,
    "early_bird_discount": keep,
    "booked_at": keep,
    "amount_due": keep,
    "shelved": keep,
    "state": keep,
    "created_at": keep,
    "booking_expires_at": keep,
    "created_online": keep,
    "erased_at": keep,
}

BOOKING_MAPPED_FIELD_GROUPS = [
    (
        "account_id",  # Makes the mapping specific to different accounts.
        "first_name",
        "last_name",
    ),
    (
        "account_id",
        "address_line1",
        "address_line2",
        "address_city",
        "address_county" "address_country",
        "address_post_code",
    ),
    (
        "account_id",
        "email",
    ),
]


# Anonymising Application and other models:
#
# - We try to keep non-sensitive data for realistic values
#
# - We preserve structure (FKs)
#
# - We have a lot of repeated data in Application and other models (the users
#   fill in the same data year after year). In some cases this makes a
#   difference to functionality (e.g. matching referees to previously defined
#   referees, where we don't have proper FKs to do matching, and functionality
#   that displays differences from one year to the next). So, we have some
#   mapping functionality defined below to keep the same random value that
#   was used the first time for the input value.
#
# - Since we are keeping FKs/PKs, and we assume our application might leak PKs
#   (via URLs etc), we have to be paranoid about removing/randomising
#   potentially sensitive information e.g. even the existence of text in
#   `youth_work_declined' is something we should hide.


APPLICATION_FIELD_MAP: dict[str, Fixer[officers.Application, object]] = {
    "id": keep,
    "officer": keep,
    "full_name": lambda f, application, v: application.officer.full_name,
    "address_firstline": address_line_1,
    "address_town": city,
    "address_county": county,
    "address_postcode": post_code,
    "address_country": country,
    "address_tel": phone_number,
    "address_mobile": mobile_number,
    "address_email": lambda f, application, v: application.officer.email,
    "christian_experience": similar_length_text,
    "youth_experience": similar_length_text,
    "youth_work_declined": const(False),
    "youth_work_declined_details": make_empty,
    "relevant_illness": const(False),
    "illness_details": make_empty,
    "dietary_requirements": make_empty,
    "crime_declaration": const(False),
    "crime_details": make_empty,
    "court_declaration": const(False),
    "court_details": make_empty,
    "concern_declaration": const(False),
    "concern_details": make_empty,
    "allegation_declaration": const(False),
    "dbs_number": lambda f, a, v: str(faker.random_number(digits=10)) if v else "",
    "dbs_check_consent": const(True),
    "finished": keep,
    "saved_on": keep,
    "birth_date": make_birth_date_adult,
    "birth_place": application_birth_place,
}

APPLICATION_MAPPED_FIELD_GROUPS = [
    (
        "officer_id",  # This makes the mapping specific to each officer, rather than shared.
        "address_firstline",
        "address_town",
        "address_county",
        "address_postcode",
        "address_country",
    ),
    (
        "officer_id",
        "address_tel",
    ),
    (
        "officer_id",
        "birth_place",
    ),
    (
        "officer_id",
        "address_mobile",
    ),
    (
        "officer_id",
        "dbs_number",
    ),
]


REFEREE_FIELD_MAP: dict[str, Fixer[officers.Referee, object]] = {
    "referee_number": keep,
    "name": full_name,
    "address": address_line_1,
    "tel": phone_number,
    "mobile": mobile_number,
    "capacity_known": similar_length_text,
    "email": email_from_name,
}

# Referees are almost always the same from one year to the next,
# and for testing it's helpful to preserve this structure
REFEREE_MAPPED_FIELD_GROUPS = [
    # Using 'email' as a pseudo ID for referee here,
    # we make a set of mappings that are specific to different referees.
    ("email",),
    ("email", "name"),
    ("email", "capacity_known"),
    (
        "email",
        "address",
    ),
    (
        "email",
        "tel",
    ),
    (
        "email",
        "mobile",
    ),
]

REFERENCE_FIELD_MAP: dict[str, Fixer[officers.Reference, object]] = {
    "referee_name": lambda f, reference, v: reference.referee.name,
    "how_long_known": keep,
    "capacity_known": keep,
    "known_offences": const(False),
    "known_offences_details": make_empty,
    "capability_children": similar_length_text,
    "character": similar_length_text,
    "concerns": const("None"),
    "comments": const("Nothing else"),
    "given_in_confidence": const(False),
    "created_on": keep,
    "inaccurate": keep,
}


USER_FIELD_MAP: dict[str, Fixer[accounts.User, object]] = {
    "contact_phone_number": lambda f, user, v: "01234 567 890" if user.contact_phone_number else "",
    # Order: first_name and last_name before username
    "first_name": first_name,
    "last_name": last_name,
    "username": auto_username,
    "email": lambda f, user, v: f"{user.username}@example.com",
    "password": dummy_password,
    "last_login": keep,
    "is_superuser": const(False),
    "is_staff": keep,
    "is_active": keep,
    "joined_at": keep,
    "bad_password": keep,
    "password_validators_used": keep,
}

PERSON_FIELD_MAP: dict[str, Fixer[cciwmain.Person, object]] = {
    "name": lambda f, person, v: " and ".join(user.full_name for user in person.users.all()),
    "info": similar_length_text,
}


# --- Overall mapping ---

MODEL_HANDLERS: dict[type, Anonymiser] = {
    # Order matters sometimes.
    accounts.User: AnonymiseWithMap(accounts.User, USER_FIELD_MAP),
    accounts.Role: AnonymiseWithMap(
        accounts.Role,
        {
            "name": keep,
            "email": keep,  # Group email, not personal
            "allow_emails_from_public": keep,
            # Others are M2M, don't directly contain personal info
        },
    ),
    # NB: Person comes after User, because it users anonymised user names
    cciwmain.Person: AnonymiseWithMap(
        cciwmain.Person,
        PERSON_FIELD_MAP,
    ),
    cciwmain.CampName: IgnoreTable(),
    cciwmain.Camp: AnonymiseWithMap(
        cciwmain.Camp,
        {
            "year": keep,
            "old_name": keep,
            "minimum_age": keep,
            "maximum_age": keep,
            "start_date": keep,
            "end_date": keep,
            "max_campers": keep,
            "max_male_campers": keep,
            "max_female_campers": keep,
            "last_booking_date": keep,
            "south_wales_transport_available": keep,
            "special_info_html": keep,
        },
    ),
    cciwmain.Site: AnonymiseWithMap(
        cciwmain.Site,
        {
            "short_name": keep,
            "slug_name": keep,
            "long_name": keep,
            "info": keep,
        },
    ),
    # Bookings
    bookings.Price: IgnoreTable(),
    bookings.CustomAgreement: IgnoreTable(),
    bookings.BookingAccount: AnonymiseWithMap(
        bookings.BookingAccount,
        BOOKINGACCOUNT_FIELD_MAP,
    ),
    bookings.Booking: AnonymiseWithMapAndGroups(
        bookings.Booking,
        BOOKING_FIELD_MAP,
        BOOKING_MAPPED_FIELD_GROUPS,
    ),
    # Applications and officers
    # NB: Application is after User, because it depends on it
    officers.Application: AnonymiseWithMapAndGroups(
        officers.Application, APPLICATION_FIELD_MAP, APPLICATION_MAPPED_FIELD_GROUPS
    ),
    officers.Referee: AnonymiseWithMapAndGroups(
        officers.Referee,
        REFEREE_FIELD_MAP,
        REFEREE_MAPPED_FIELD_GROUPS,
    ),
    officers.ReferenceAction: IgnoreTable(),
    # Reference comes after Referee, it depends on it
    officers.Reference: AnonymiseWithMap(officers.Reference, REFERENCE_FIELD_MAP),
    officers.QualificationType: IgnoreTable(),
    officers.Qualification: AnonymiseWithMap(
        officers.Qualification,
        {
            "issued_on": keep,
        },
    ),
    officers.CampRole: AnonymiseWithMap(
        officers.CampRole,
        {
            "name": keep,
        },
    ),
    officers.Invitation: AnonymiseWithMap(
        officers.Invitation,
        {
            "added_on": keep,
            "notes": make_empty,
        },
    ),
    officers.DBSCheck: AnonymiseWithMapAndGroups(
        officers.DBSCheck,
        {
            "dbs_number": same_length_number,
            "check_type": keep,
            "completed_on": keep,
            "requested_by": keep,
            "other_organisation": keep,
            "applicant_accepted": const(True),
            "registered_with_dbs_update": keep,
        },
        [
            ("dbs_number",),
        ],
    ),
    officers.DBSActionLog: AnonymiseWithMap(
        officers.DBSActionLog,
        {
            "action_type": keep,
            "created_at": keep,
        },
    ),
    # Site content:
    sitecontent.MenuLink: IgnoreTable(),
    sitecontent.HtmlChunk: IgnoreTable(),
    # Django tables:
    auth.Permission: IgnoreTable(),
    auth.Group: IgnoreTable(),  # May have mapping to user, but no personal data
    admin.LogEntry: AnonymiseWithMap(
        admin.LogEntry,
        {
            "action_time": keep,
            "object_id": keep,
            "object_repr": const("<scrubbed>"),  # This could contain personal info
            "change_message": const("<scrubbed>"),
            "action_flag": keep,
        },
    ),
    contenttypes.ContentType: IgnoreTable(),
    sessions.Session: TruncateTable(sessions.Session),
    sites.Site: IgnoreTable(),
}


# --- self tests ---
def test_anonymisation():
    """
    Check that our anonymization functions are complete
    """

    # For each model we have, check that the field list it is covering is
    # exhaustive.

    for model, anonymiser in MODEL_HANDLERS.items():
        missing = []
        model_field_list = model._meta.get_fields()
        fields_covered = anonymiser.get_fields_covered()
        for f in model_field_list:
            if isinstance(fields_covered, AllFields):
                continue

            if isinstance(f, models.ManyToOneRel | models.ManyToManyField | models.ManyToManyRel):
                # Handled by other table
                continue

            assert isinstance(f, models.Field)
            # Standard fields that don't need anonymising:
            if isinstance(f, models.AutoField | models.ForeignKey):
                continue
            if f.name == "erased_at":
                continue

            if f.name not in fields_covered:
                missing.append(f.name)

        if missing:
            assert False, f"The following fields are missing in anonymiser for {model.__name__}:\n" + "\n".join(
                f"  - {f}" for f in missing
            )

        if isinstance(fields_covered, set):
            real_field_names = set(f.name for f in model_field_list)
            unexpected_names = fields_covered - real_field_names
            if unexpected_names:
                assert False, f"The following fields for {model.__name__} are not recognised: " + ", ".join(
                    sorted(unexpected_names)
                )

    # Check that we have covered all models
    all_models = apps.get_models()

    for model in all_models:
        assert model in MODEL_HANDLERS, f"{model} needs an entry in MODEL_HANDLERS"


if __name__ == "__main__":
    main()
