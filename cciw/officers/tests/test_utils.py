from django.test import TestCase
from django.utils import timezone

from cciw.cciwmain.models import Camp
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.officers.tests.base import ExtraOfficersSetupMixin


class UtilsTests(ExtraOfficersSetupMixin, TestCase):

    def test_camp_officer_list(self):
        c = self.default_camp_1
        self.assertEqual(repr(camp_officer_list(c)), "[<User: fredjones>, <User: joebloggs>, <User: petersmith>]")

    def test_camp_slacker_list(self):
        c = self.default_camp_1
        self.officer1.applications.create(finished=True, date_submitted="2000-01-01")
        self.assertEqual(repr(camp_slacker_list(c)), "[<User: fredjones>, <User: petersmith>]")
