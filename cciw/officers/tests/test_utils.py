from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.tests import factories as factories
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.utils.tests.base import TestBase


class UtilsTests(TestBase):
    def test_camp_officer_list(self):
        camp = camp_factories.create_camp()
        factories.add_officers_to_camp(
            camp,
            [
                factories.create_officer(username="joebloggs"),
                factories.create_officer(username="anneandrews"),
            ],
        )
        assert [u.username for u in camp_officer_list(camp)] == ["anneandrews", "joebloggs"]

    def test_camp_slacker_list(self):
        camp = camp_factories.create_camp()
        factories.add_officers_to_camp(
            camp,
            [
                (officer1 := factories.create_officer(username="joebloggs")),
                factories.create_officer(username="anneandrews"),
            ],
        )
        factories.create_application(officer=officer1, year=camp.year, finished=True)
        assert [u.username for u in camp_slacker_list(camp)] == ["anneandrews"]
