# Run this with:

#   locust --config scripts/attic/bookings_load_test_2025.conf
from __future__ import annotations

from functools import cached_property

from faker import Faker
from locust import HttpUser, SequentialTaskSet, between, task

from cciw.utils.loadtests.page import Page


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
        assert "email has been sent" in self.page.last_response.html.text

    @task
    def bookings_login(self):
        # TODO - cheat the login by making a token by the back door.
        self.page.go("/booking/start/")


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
