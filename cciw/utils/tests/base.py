"""
Base classes and base utilities for all tests.
"""

import logging
from datetime import date

import time_machine
from django.conf import settings
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
    def setUp(self):
        super().setUp()
        import cciw.cciwmain.common

        cciw.cciwmain.common._thisyear = None
        cciw.cciwmain.common._thisyear_timestamp = None

        # To get our custom email backend to be used, we have to patch settings
        # at this point, due to how Django's test runner also sets this value:
        settings.EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"


class TestBase(TestBaseMixin, TestCase):
    pass


class disable_logging(TestContextDecorator):
    def enable(self):
        logging.disable(logging.CRITICAL)

    def disable(self):
        logging.disable(logging.NOTSET)
