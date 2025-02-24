"""
Base classes and base utilities for all tests.
"""

import logging
import os
from datetime import date, datetime
from unittest import mock

import time_machine
from django.conf import settings
from django.core import mail
from django.db.transaction import Atomic
from django.test import TestCase
from django.test.utils import TestContextDecorator


class TimeTravelMixin:
    """
    Run all tests as if on on the day specified by `today` attribute
    """

    today: date = NotImplemented

    def setUp(self):
        super().setUp()
        if self.today is NotImplemented and "TEST_DATE" in os.environ:
            # This mechanism allows us to simulate running tests at different times
            # of the year. This is needed because of the way that some tests factories
            # do interesting things with dates e.g. create_camp()
            self.today = datetime.strptime(os.environ["TEST_DATE"], "%Y-%m-%d")
        if self.today is not NotImplemented:
            self.traveller = time_machine.travel(self.today)
            self.traveller.start()
        else:
            self.traveller = None

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

        mail.queued_outbox = []


class AtomicChecksMixin:
    def setUp(self):
        super().setUp()
        # We want to ensure that inside transactions we don't send mail using
        # the normal method (which uses an HTTP API), for two reasons:
        #
        # - random network failures would throw exceptions and probably cause
        #   the transaction to be rolled back, which normally we want to avoid.
        #   For example, email failure shouldn't stop places being booked.
        #
        # - if the transaction is rolled back for some other reason, we don't
        #   want the related email to be sent e.g. we don't want to send
        #   "your place has been booked" if in the end it wasn't.

        # So, instead should use 'queued_mail' for mail, which stores something
        # on the DB and therefore participates in transactions.

        # (At the same time, it's better to use non-queued mail for other
        # things, so that the email is sent immediately, and they use gets
        # immediate feedback if the email actually fails to send, so we don't use
        # queued email for everything).

        # Currently, we only enforce this within some parts of the code base
        # (bookings), so this mixin is not a part of TestBaseMixin.
        # Ideally AtomicChecksMixin would be part of TestBaseMixin, but currently
        # it causes lots of failures generally in admin

        # To enforce the checks, we rely on:
        # - using `EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"` while running tests.
        # - monkey patching Atomic to add asserts, below

        from cciw.mail.tests import disable_nonqueued_email_sending, enable_nonqueued_email_sending

        original_Atomic_enter = Atomic.__enter__
        original_Atomic_exit = Atomic.__exit__

        def replacement_Atomic_enter(self):
            disable_nonqueued_email_sending()
            original_Atomic_enter(self)

        def replacement_Atomic_exit(self, exc_type, exc_value, traceback):
            enable_nonqueued_email_sending()
            original_Atomic_exit(self, exc_type, exc_value, traceback)

        self.Atomic_enter_patcher = mock.patch("django.db.transaction.Atomic.__enter__", replacement_Atomic_enter)
        self.Atomic_exit_patcher = mock.patch("django.db.transaction.Atomic.__exit__", replacement_Atomic_exit)
        self.Atomic_enter_patcher.start()
        self.Atomic_exit_patcher.start()

    def tearDown(self):
        self.Atomic_enter_patcher.stop()
        self.Atomic_exit_patcher.stop()
        super().tearDown()


class TestBase(TestBaseMixin, TestCase):
    pass


class disable_logging(TestContextDecorator):
    def enable(self):
        logging.disable(logging.CRITICAL)

    def disable(self):
        logging.disable(logging.NOTSET)
