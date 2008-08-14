from cciw.cciwmain.models import Camp
from cciw.officers import utils
from django.test import TestCase


class UtilsTests(TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']

    def test_camp_officer_list(self):
        c = Camp.objects.get(pk=1)
        self.assertEqual(repr(utils.camp_officer_list(c)), "[<User: davestott>, <User: mrofficer2>, <User: officer3>]")

    def test_camp_slacker_list(self):
        c = Camp.objects.get(pk=1)
        self.assertEqual(repr(utils.camp_slacker_list(c)), "[<User: davestott>]")
