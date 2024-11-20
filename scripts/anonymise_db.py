"""
Functions to remove sensitive user information
"""

# ruff: noqa:E402

# Used as a one-off to produce a DB that had realistic amounts/structure of data
# but can be shared without problems.

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

import django

django.setup()

import tqdm
from django.apps import apps
from django.contrib.auth import models as auth
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
    if isinstance(field, models.CharField):
        return ""
    return None


def keep(field, instance, value):
    return value


def similar_length_text(field, instance, value):
    return faker.text(max_nb_chars=len(value)) if len(value) > 10 else ""


def const(constant_val) -> Fixer:
    return lambda field, instance, value: constant_val


def make_birth_date_adult(field, instance, value) -> date:
    return faker.date_of_birth(minimum_age=18)


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
        pass

    def get_fields_covered(self) -> AllFields:
        return AllFields()


def anonymize_model_with_map_and_groups(
    model: type, field_map: dict[str, Fixer], mapped_field_groups: list[tuple[str]]
):
    maps = {k: {} for k in mapped_field_groups}
    all_qs = model.objects.all()
    count = all_qs.count()
    for instance in tqdm.tqdm(all_qs, total=count):
        fields_needed_for_mapped_values = set(attr for attr_group in mapped_field_groups for attr in attr_group)
        saved_field_values = {f: getattr(instance, f) for f in fields_needed_for_mapped_values}

        corrected_fields = []

        # If we already mapped some fields, use mapped values:
        for attr_group in mapped_field_groups:
            mapped_vals = maps[attr_group]
            vals = tuple(getattr(instance, attr) for attr in attr_group)
            if vals in mapped_vals:
                new_vals = mapped_vals[vals]
                for attr, new_val in zip(attr_group, new_vals):
                    setattr(instance, attr, new_val)
                corrected_fields.extend(attr_group)

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
            maps[attr_group][old_values] = [getattr(instance, attr) for attr in attr_group]

        instance.save()


# --- specific models ---


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


APPLICATION_FIELD_MAP: dict[str, Fixer[officers.Application, Any]] = {
    "id": keep,
    "officer": keep,
    "full_name": lambda f, application, v: application.officer.full_name,
    "address_firstline": lambda f, a, v: faker.address().split("\n")[0] if v else "",
    "address_town": lambda f, a, v: faker.city() if v else "",
    "address_county": lambda f, a, v: faker.county() if v else "",
    "address_postcode": lambda f, a, v: faker.postcode() if v else "",
    "address_country": lambda f, a, v: faker.country() if v else "",
    "address_tel": lambda f, a, v: faker.phone_number() if v else "",
    "address_mobile": lambda f, a, v: faker.phone_number() if v else "",
    "address_email": lambda f, application, v: application.officer.email,
    "christian_experience": similar_length_text,
    "youth_experience": similar_length_text,
    "youth_work_declined": const(False),
    "youth_work_declined_details": const(""),
    "relevant_illness": const(False),
    "illness_details": const(""),
    "dietary_requirements": const(""),
    "crime_declaration": const(False),
    "crime_details": const(""),
    "court_declaration": const(False),
    "court_details": const(""),
    "concern_declaration": const(False),
    "concern_details": const(""),
    "allegation_declaration": const(False),
    "dbs_number": lambda f, a, v: str(faker.random_number(digits=10)) if v else "",
    "dbs_check_consent": const(True),
    "finished": keep,
    "saved_on": keep,
    "birth_date": make_birth_date_adult,
    "birth_place": lambda f, a, v: faker.city() if v else "",
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


USER_FIELD_MAP: dict[str, Fixer[accounts.User, Any]] = {
    "contact_phone_number": lambda f, user, v: "01234 567 890" if user.contact_phone_number else "",
    # Order: first_name and last_name before username
    "first_name": lambda f, user, v: faker.first_name(),
    "last_name": lambda f, user, v: faker.last_name(),
    "username": auto_username,
    "email": lambda f, user, v: f"{user.username}@example.com",
    "password": dummy_password,
    "last_login": keep,
    "is_superuser": const(False),
    "is_staff": keep,
    "is_active": keep,
    "joined_at": keep,
}


# TODO convert this


# def anonymize_booking_data():
#     for account in BookingAccount.objects.all():
#         account.name = faker.name()
#         account.email = (
#             account.name.replace(" ", ".").replace("'", "").replace("’", "")
#             + abs(hash(account.email)) % 1000
#             + "@example.com"
#         )
#         # TODO the rest
#         account.save()

#     # For bookings, we want to preserve names similar to how we preserve emails in other places


# --- Overall mapping ---

MODEL_HANDLERS: dict[type, Anonymiser] = {
    # Order matters sometimes.
    accounts.User: AnonymiseWithMap(accounts.User, USER_FIELD_MAP),
    # Application is after User, because it depends on it
    officers.Application: AnonymiseWithMapAndGroups(
        officers.Application, APPLICATION_FIELD_MAP, APPLICATION_MAPPED_FIELD_GROUPS
    ),
    # Django tables:
    auth.Permission: IgnoreTable(),
    auth.Group: IgnoreTable(),  # May have mapping to user, but no personal data
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
        if isinstance(anonymiser, AnonymiseWithMapAndGroups):
            model_field_list = model._meta.get_fields()
            for f in model_field_list:
                if isinstance(f, models.ManyToOneRel | models.ManyToManyField):
                    # Handled by other table
                    continue

                assert isinstance(f, models.Field)
                # Standard fields that don't need anonymising:
                if isinstance(f, models.AutoField | models.ForeignKey):
                    continue
                if f.name == "erased_at":
                    continue

                if f.name not in anonymiser.field_map:
                    missing.append(f.name)
        elif isinstance(anonymiser, IgnoreTable):
            # No missing fields
            missing = []
        else:
            raise NotImplementedError(f"Unhandled anonymiser type {anonymiser.__class__.__name__}")

        if missing:
            assert False, f"The following fields are missing in anonymiser for {model.__name__}:\n" + "\n".join(
                f"  - {f}" for f in missing
            )

    # Check that we have covered all models
    all_models = apps.get_models()

    for model in all_models:
        assert model in MODEL_HANDLERS, f"{model} needs an entry in MODEL_HANDLERS"


if __name__ == "__main__":
    main()
