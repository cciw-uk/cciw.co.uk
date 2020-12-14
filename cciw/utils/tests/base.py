import logging
from unittest import mock

from django.conf import settings
from django.db.transaction import Atomic
from django.test import TestCase
from django.test.utils import TestContextDecorator


class TestBaseMixin:

    def setUp(self):
        super().setUp()
        import cciw.cciwmain.common
        cciw.cciwmain.common._thisyear = None

        # To get our custom email backend to be used, we have to patch settings
        # at this point, due to how Django's test runner also sets this value:
        settings.EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"


class AtomicChecksMixin(object):
    def setUp(self):
        super().setUp()
        # We want to ensure that inside transactions we don't send mail using
        # the normal method (which uses an HTTP API), or anything else that does
        # something that could fail depending on random network failures. We
        # instead should use 'queued_mail' for mail, which stores something on
        # the DB and therefore participates in transactions.

        # Currently, we only enforce this within some parts of the code base
        # (bookings), so this mixin is not a part of TestBaseMixin.
        # Ideally AtomicChecksMixin would be part of TestBaseMixin, but currently
        # it causes lots of failures generally in admin
        from cciw.mail.tests import disable_email_sending, enable_email_sending

        # So, for tests only, we monkey patch Atomic to add asserts
        original_Atomic_enter = Atomic.__enter__
        original_Atomic_exit = Atomic.__exit__

        def replacement_Atomic_enter(self):
            disable_email_sending()
            original_Atomic_enter(self)

        def replacement_Atomic_exit(self, exc_type, exc_value, traceback):
            enable_email_sending()
            original_Atomic_exit(self, exc_type, exc_value, traceback)

        self.Atomic_enter_patcher = mock.patch('django.db.transaction.Atomic.__enter__',
                                               replacement_Atomic_enter)
        self.Atomic_exit_patcher = mock.patch('django.db.transaction.Atomic.__exit__',
                                              replacement_Atomic_exit)
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
