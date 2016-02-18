from django.test import TestCase


class TestBaseMixin(object):

    def setUp(self):
        super(TestBaseMixin, self).setUp()
        import cciw.cciwmain.common
        cciw.cciwmain.common._thisyear = None


class TestBase(TestBaseMixin, TestCase):
    pass
