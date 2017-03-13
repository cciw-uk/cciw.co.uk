import logging

from django.conf import settings
from django.test import TestCase
from django.test.utils import TestContextDecorator


class TestBaseMixin(object):

    def setUp(self):
        super(TestBaseMixin, self).setUp()
        import cciw.cciwmain.common
        cciw.cciwmain.common._thisyear = None

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
