# ruff: noqa:E402

# Run this with:

#   locust --config scripts/attic/bookings_load_test_2025.conf
from __future__ import annotations

import subprocess

import django

django.setup()

import random
from datetime import date
from functools import cached_property
from typing import Literal, cast

import requests
from attr import dataclass
from django.conf import settings
from faker import Faker
from locust import HttpUser, SequentialTaskSet, between, task

from cciw.bookings.email import EmailVerifyTokenGenerator, build_url_with_booking_token
from cciw.bookings.models import PriceType
from cciw.utils.loadtests.page import Page

STAGING_DOMAIN = "staging.cciw.co.uk"


class FakePersonData:
    def __init__(self) -> None:
        self._faker = Faker("en_GB")

    @cached_property
    def email(self) -> str:
        return (
            f"{self.full_name.replace(' ','.')}{abs(hash(self.full_name + self.address_post_code)) % 1000}@example.com"
        )

    @cached_property
    def address_line1(self) -> str:
        return self._faker.address().split("\n")[0]

    @cached_property
    def address_city(self) -> str:
        return self._faker.city()

    @cached_property
    def address_country(self) -> str:
        return "GB"

    @cached_property
    def address_post_code(self) -> str:
        return self._faker.postcode()

    @cached_property
    def address_phone_number(self) -> str:
        return self._faker.phone_number()

    @cached_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @cached_property
    def first_name(self):
        return self._faker.first_name()

    @cached_property
    def last_name(self):
        return self._faker.last_name()


@dataclass
class FakeCamp:
    id: int
    year: int
    minimum_age: int
    maximum_age: int


# Easiest way to get camp IDs on staging site is just to copy data in:
ALL_CAMPS: list[FakeCamp] = [
    FakeCamp(id=152, year=2025, minimum_age=17, maximum_age=22),
    FakeCamp(id=153, year=2025, minimum_age=11, maximum_age=17),
    FakeCamp(id=154, year=2025, minimum_age=11, maximum_age=17),
    FakeCamp(id=155, year=2025, minimum_age=11, maximum_age=17),
    FakeCamp(id=156, year=2025, minimum_age=11, maximum_age=17),
    FakeCamp(id=157, year=2025, minimum_age=11, maximum_age=17),
]


class FakeCamperData(FakePersonData):
    @cached_property
    def camp(self) -> FakeCamp:
        return random.choice(ALL_CAMPS)

    @cached_property
    def birth_date(self) -> date:
        # Pick age appropriate for the camp, assumed to be junior camp, 2025:
        age = int((self.camp.maximum_age + self.camp.minimum_age) / 2)
        return date(self.camp.year - age, 1, 1)

    @cached_property
    def sex(self) -> Literal["m", "f"]:
        return random.choice(["m", "f"])


class FakeBookingAccountData(FakePersonData):
    # A booking account is a person,
    # and has some more related people:

    @cached_property
    def gp(self) -> FakePersonData:
        return FakePersonData()

    def get_new_camper_place_details(self) -> FakeCamperData:
        camper = FakeCamperData()
        camper.last_name = self.last_name
        return camper


class BookPlaceTaskSet(SequentialTaskSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page = Page(client=self.client)

    @property
    def user(self) -> BookingUser:
        return cast(BookingUser, super().user)

    @property
    def client(self) -> requests.Session:
        return super().client

    # -- START TASKS --

    @task
    def bookings_index(self):
        self.client.get("/booking/")

    @task
    def bookings_start(self):
        self.page.go("/booking/start/")
        self.page.fill({"#id_email": self.user.data.email})
        self.wait()
        self.page.submit()
        assert self.page.last_response is not None
        assert "email has been sent" in self.page.last_response.text

    @task
    def bookings_main(self):
        # Login
        data: FakePersonData = self.user.data
        self.page.go(_booking_login_url(data.email))
        assert self.page.last_response is not None
        assert self.page.last_url is not None
        message = f"Logged in as {data.email}!"
        assert message in self.page.last_response.text

        if self.page.last_url.endswith("/booking/account/"):
            self.wait()
            self.do_account_details_page()

        self.wait()
        self.do_add_new_booking()

        # In 2025: stats:
        #  - Total 328 accounts attempted to book
        #  - 207 created single booking
        #  - 83 created 2 bookings
        #  - 38 created 3 or more

        #  So about (328 - 207)/328 =  37% created more than one:
        if random.randrange(0, 100) <= 37:
            # Second child
            self.wait()
            self.do_add_new_booking()

            # Of these, 38 / (83 + 38) = 35% created more than two:
            if random.randrange(0, 100) <= 35:
                # Third child
                self.wait()
                self.do_add_new_booking()

        if not self.page.last_url.endswith("/booking/checkout/"):
            self.page.go("/booking/checkout/")

        self.page.submit("[name=book_now]")

    # Always at end: logout, so that the process can start again without errors
    @task
    def bookings_logout(self):
        self.client.cookies.clear()

    # -- END TASKS --

    def do_account_details_page(self):
        data = self.user.data
        self.page.fill(
            {
                "#id_name": data.full_name,
                "#id_address_line1": data.address_line1,
                "#id_address_city": data.address_city,
                "#id_address_country": data.address_country,
                "#id_address_post_code": data.address_post_code,
            }
        )
        self.page.submit()
        assert self.page.last_response is not None
        assert "Account details updated, thank you." in self.page.last_response.text

    def do_add_new_booking(self) -> None:
        assert self.page.last_url is not None
        assert self.page.last_response is not None
        if not self.page.last_url.endswith("/booking/add-camper-details/"):
            self.page.go("/booking/add-camper-details/")
        place_details, camper = self.get_booking_details()

        # While the user fills in details, for each field we'll get a validation
        # request sent by htmx. These will happen at the same time as everything
        # else, so we use an external process to launch in parallel without
        # waiting for it to finish, - if we use self.client then we'll get
        # serial behaviour.
        for css_selector, value in place_details.items():
            if isinstance(value, bool):
                continue  # checkboxes excluded
            import furl

            if not css_selector.startswith("#id_"):
                continue

            field_name = css_selector.replace("#id_", "")

            # Not all of these will be exactly what a browser sends, but we should get enough.
            validation_url = str(
                furl.furl(
                    url="https://staging.cciw.co.uk/booking/add-camper-details/",
                    query_params={field_name: value, "_validate_field": field_name},
                )
            )
            assert f"&_validate_field={field_name}" in validation_url
            htmx_headers = {
                "HX-Request": "true",
                "HX-Trigger": "div_id_last_name",
                "HX-Target": "div_id_last_name",
                "HX-Current-URL": "https://staging.cciw.co.uk/booking/add-camper-details/",
            }
            # The following with the help of browser tools
            last_headers = self.page.last_response.response.request.headers
            headers = dict(last_headers) | htmx_headers
            curl_headers = [h for key, value in headers.items() for h in ["-H", f"{key}: {value}"]]
            cmd = (
                [
                    "curl",
                    "--compressed",
                    "--insecure",
                ]
                + curl_headers
                + [validation_url]
            )
            subprocess.Popen(cmd)

        # It takes a while to fill in details:
        for i in range(0, random.randint(1, 4)):
            self.wait()
        self.page.fill(place_details)
        self.page.submit()
        assert f'Details for "{camper.full_name}" were saved successfully'

    def get_booking_details(self) -> tuple[dict, FakeCamperData]:
        user_data = self.user.data
        camper = user_data.get_new_camper_place_details()
        camp = camper.camp

        return {
            "[name=camp]": camper.camp.id,
            "#id_price_type": PriceType.FULL,
            "#id_first_name": camper.first_name,
            "#id_last_name": camper.last_name,
            "#id_sex": camper.sex,
            "#id_birth_date": camper.birth_date.isoformat(),
            "#id_address_line1": user_data.address_line1,
            "#id_address_city": user_data.address_city,
            "#id_address_country": user_data.address_country,
            "#id_address_post_code": user_data.address_country,
            "#id_contact_name": user_data.full_name,
            "#id_contact_line1": user_data.address_line1,
            "#id_contact_city": user_data.address_city,
            "#id_contact_country": user_data.address_country,
            "#id_contact_post_code": user_data.address_post_code,
            "#id_contact_phone_number": user_data.address_phone_number,
            "#id_gp_name": user_data.gp.full_name,
            "#id_gp_line1": user_data.gp.address_line1,
            "#id_gp_city": user_data.gp.address_city,
            "#id_gp_country": user_data.gp.address_country,
            "#id_gp_post_code": user_data.gp.address_post_code,
            "#id_gp_phone_number": user_data.gp.address_phone_number,
            "#id_medical_card_number": "asdfasdf",
            "#id_last_tetanus_injection_date": date(camp.year - 5, 2, 3),
            "#id_serious_illness": False,
            "#id_agreement": True,
        }, camper


def _booking_login_url(email: str) -> str:
    # Cheat the login by making a token directly
    view_name = "cciw-bookings-verify_and_continue"
    verify_url = build_url_with_booking_token(
        view_name=view_name, email=email, domain=STAGING_DOMAIN, token_generator=make_staging_EmailVerifyTokenGenerator
    )
    return verify_url


def make_staging_EmailVerifyTokenGenerator() -> EmailVerifyTokenGenerator:
    staging_secret_key = settings.SECRETS["STAGING_SECRET_KEY"]
    return EmailVerifyTokenGenerator(key=staging_secret_key)


class BookingUser(HttpUser):
    @cached_property
    def data(self):
        return FakeBookingAccountData()

    def on_start(self):
        # Disable SSL verifcation, we are using certificates from staging instance of LetsEncrypt
        """on_start is called when a Locust start before any task is scheduled"""
        self.client.verify = False

    wait_time = between(2, 8)
    tasks = [BookPlaceTaskSet]
