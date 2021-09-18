"""
Base classes and base utilities for all tests.
"""
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
        cciw.cciwmain.common._thisyear_timestamp = None

        # To get our custom email backend to be used, we have to patch settings
        # at this point, due to how Django's test runner also sets this value:
        settings.EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"

    def tearDown(self):
        FactoriesBase.clear_instances()
        super().tearDown()


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


class FactoriesBase:
    _all_factory_instances = []

    def __new__(cls):
        instance = super().__new__(cls)
        FactoriesBase._all_factory_instances.append(instance)
        return instance

    @staticmethod
    def clear_instances():
        # Model factories cache created instances, which is problematic
        # when the object is re-used for the next test, but the record
        # doesn't exist in the database.

        # We cannot easily delete instances, because there are references to
        # them in other modules. But we can reset them to a pristine
        # condition, by creating a new instance and assigning __dict__

        # Avoid infinite loop by making a copy of _all_factory_instances
        instances = FactoriesBase._all_factory_instances[:]
        for instance in instances:
            instance.__dict__ = instance.__class__().__dict__
        # Discard the new instances we just created above
        FactoriesBase._all_factory_instances = instances

        # We also want to clear @lru_cache() on all methods
        for subclass in FactoriesBase.__subclasses__():
            for k, val in subclass.__dict__.items():
                if hasattr(val, 'cache_clear'):
                    val.cache_clear()
