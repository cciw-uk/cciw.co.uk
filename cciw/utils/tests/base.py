"""
Base classes and base utilities for all tests.
"""

import logging
from datetime import date

import time_machine
from django.test import TestCase
from django.test.utils import TestContextDecorator


class TimeTravelMixin:
    """
    Run all tests as if on on the day specified by `today` attribute
    """

    today: date = NotImplemented

    def setUp(self):
        super().setUp()
        today = self.get_today()
        if today is not NotImplemented:
            self.traveller = time_machine.travel(self.today)
            self.traveller.start()
        else:
            self.traveller = None

    def get_today(self):
        return self.today

    def tearDown(self):
        if self.traveller is not None:
            self.traveller.stop()
        super().tearDown()


class TestBaseMixin(TimeTravelMixin):
    # Most things should actually go in `cciw_all` fixture
    pass


class TestBase(TestBaseMixin, TestCase):
    pass


class disable_logging(TestContextDecorator):
    def enable(self):
        logging.disable(logging.CRITICAL)

    def disable(self):
        logging.disable(logging.NOTSET)
