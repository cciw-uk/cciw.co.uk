from django_functest import FuncBaseMixin

from cciw.cciwmain.models import Camp
from cciw.officers.views import get_officers_with_dbs_info_for_camps
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase

from .base import SECRETARY, SimpleOfficerSetupMixin, DefaultApplicationsMixin, CreateApplicationMixin


class DbsInfo(SimpleOfficerSetupMixin, CreateApplicationMixin, TestBase):
    def setUp(self):
        super(DbsInfo, self).setUp()
        self.year = 2000
        self.camp = self.default_camp_1
        self.camp.invitations.create(officer=self.officer_user)

    def get_officer_with_dbs_info(self):
        camps = Camp.objects.filter(year=self.year)
        officers_and_dbs_info = get_officers_with_dbs_info_for_camps(camps, set(camps))
        relevant = [(o, c) for o, c in officers_and_dbs_info
                    if o == self.officer_user]
        assert len(relevant) == 1
        return relevant[0]

    def test_requires_action_no_application_form(self):
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertFalse(dbs_info.requires_action)

    def test_requires_action_with_application_form(self):
        self.create_application(self.officer_user, self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertTrue(dbs_info.requires_action)


class ManageDbsPageBase(DefaultApplicationsMixin, FuncBaseMixin):

    def test_view_no_application_forms(self):
        camp = self.default_camp_1
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', camp.year)
        self.assertCode(200)
        self.assertTextPresent("Manage DBSs 2000 | CCIW Officers")

        officers = [i.officer for i in camp.invitations.all()]
        self.assertNotEqual(len(officers), 0)
        for officer in officers:
            # Sanity check assumptions
            self.assertEqual(officer.applications.count(), 0)

            # Actual test
            self.assertTextPresent(officer.first_name)
            self.assertTextPresent(officer.last_name)

        self.assertTextPresent('Needs application form')

    def test_view_with_application_forms(self):
        self.create_default_applications()
        camp = self.default_camp_1
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', camp.year)
        self.assertTextAbsent('Needs application form')


class ManageDbsPageWT(ManageDbsPageBase, WebTestBase):
    pass


class ManageDbsPageSL(ManageDbsPageBase, SeleniumBase):
    def test_log_dbs_sent(self):
        self.create_default_applications()
        camp = self.default_camp_1
        officer = self.officer1
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', camp.year)

        self.assertEqual(officer.dbsformlogs.count(), 0)

        self.click('#id_send_{0}'.format(officer.id))
        self.wait_for_ajax()

        self.assertEqual(officer.dbsformlogs.count(), 1)

        self.click('#id_undo_{0}'.format(officer.id))
        self.wait_for_ajax()

        self.assertEqual(officer.dbsformlogs.count(), 0)
