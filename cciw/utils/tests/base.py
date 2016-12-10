import logging

from django.test import TestCase
from django.test.utils import TestContextDecorator


class TestBaseMixin(object):

    def setUp(self):
        super(TestBaseMixin, self).setUp()
        import cciw.cciwmain.common
        cciw.cciwmain.common._thisyear = None


class TestBase(TestBaseMixin, TestCase):
    pass


class disable_logging(TestContextDecorator):
    def enable(self):
        logging.disable(logging.CRITICAL)

    def disable(self):
        logging.disable(logging.NOTSET)
