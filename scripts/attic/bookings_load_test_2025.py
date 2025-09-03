# ruff: noqa:E402

# Run this with:

#   locust --config scripts/attic/bookings_load_test_2025.conf
from __future__ import annotations

from typing import cast

import django
import requests

django.setup()

from functools import cached_property

from django.conf import settings
from faker import Faker
from locust import HttpUser, SequentialTaskSet, between, task

from cciw.bookings.email import EmailVerifyTokenGenerator, build_url_with_booking_token
from cciw.utils.loadtests.page import Page

STAGING_DOMAIN = "staging.cciw.co.uk"


class FakeUserData:
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
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @cached_property
    def first_name(self):
        return self._faker.first_name()

    @cached_property
    def last_name(self):
        return self._faker.last_name()


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

    @task
    def start_page(self):
        self.client.get("/")

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
        data: FakeUserData = self.user.data
        self.page.go(_booking_login_url(data.email))
        assert self.page.last_response is not None
        assert self.page.last_url is not None
        message = f"Logged in as {data.email}!"
        assert message in self.page.last_response.text

        if self.page.last_url.endswith("/booking/account/"):
            self.do_account_details_page()

        # TODO:

        # - fill in camp place details - long form - copy from tests
        # - choose 'book now'

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

    # Always at end: logout, so that the process can start again without errors
    @task
    def bookings_logout(self):
        self.client.cookies.clear()


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
        return FakeUserData()

    def on_start(self):
        # Disable SSL verifcation, we are using certificates from staging instance of LetsEncrypt
        """on_start is called when a Locust start before any task is scheduled"""
        self.client.verify = False

    wait_time = between(2, 8)
    tasks = [BookPlaceTaskSet]
