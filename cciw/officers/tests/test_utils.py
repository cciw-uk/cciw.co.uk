from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.utils.tests.base import TestBase


class UtilsTests(ExtraOfficersSetupMixin, TestBase):
    def test_camp_officer_list(self):
        c = self.default_camp_1
        assert [u.username for u in camp_officer_list(c)] == ["fredjones", "joebloggs", "petersmith"]

    def test_camp_slacker_list(self):
        c = self.default_camp_1
        self.officer1.applications.create(finished=True, date_saved="2000-01-01")
        assert [u.username for u in camp_slacker_list(c)] == ["fredjones", "petersmith"]
