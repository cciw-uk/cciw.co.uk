# ruff: noqa:E402

# Run this with:

#   locust --config scripts/attic/bookings_load_test_2025.conf
from __future__ import annotations

import django

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
        self._faker = Faker()

    @cached_property
    def email(self) -> str:
        return self._faker.email()


class BookPlaceTaskSet(SequentialTaskSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page = Page(client=self.user.client)

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
    def bookings_login(self):
        data: FakeUserData = self.user.data
        self.page.go(_booking_login_url(data.email))
        assert self.page.last_response is not None
        message = f"Logged in as {data.email}!"
        assert message in self.page.last_response.text

        # TODO:
        # - fill in account details and save.
        #   - this might be conditional if the account for the email address already exists

        # - fill in camp place details - long form - copy from tests
        # - choose 'book now'

        # - when done, log out, so that we can start the process again
        #   without errors


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

    wait_time = between(2, 15)
    tasks = [BookPlaceTaskSet]
