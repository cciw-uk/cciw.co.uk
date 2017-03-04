from django_functest import FuncBaseMixin

from cciw.cciwmain.models import Camp
from cciw.officers.views import get_officers_with_dbs_info_for_camps
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase

from .base import SECRETARY, SimpleOfficerSetupMixin, OfficersSetupMixin, CreateApplicationMixin


class DbsInfo(SimpleOfficerSetupMixin, CreateApplicationMixin, TestBase):
    def setUp(self):
        super(DbsInfo, self).setUp()
        self.camp = self.default_camp_1
        self.year = self.camp.year
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


class ManageDbsPageBase(OfficersSetupMixin, CreateApplicationMixin, FuncBaseMixin):
    def setUp(self):
        super(ManageDbsPageBase, self).setUp()
        self.camp = self.default_camp_1
        self.year = self.camp.year
        self.camp.invitations.create(officer=self.officer_user)

    def test_view_no_application_forms(self):
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', self.year)
        self.assertCode(200)
        self.assertTextPresent("Manage DBSs 2000 | CCIW Officers")

        officers = [i.officer for i in self.camp.invitations.all()]
        self.assertNotEqual(len(officers), 0)
        for officer in officers:
            # Sanity check assumptions
            self.assertEqual(officer.applications.count(), 0)

            # Actual test
            self.assertTextPresent(officer.first_name)
            self.assertTextPresent(officer.last_name)

        self.assertTextPresent('Needs application form')

    def test_view_with_application_forms(self):
        self.create_application(self.officer_user, self.year)
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', self.year)
        self.assertTextAbsent('Needs application form')

    def test_log_dbs_sent(self):
        self.create_application(self.officer_user, self.year)
        officer = self.officer_user
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', self.year)
        url = self.current_url

        self.assertEqual(officer.dbsformlogs.count(), 0)

        self.click_dbs_sent_button(officer)
        # should be on same page
        self.assertUrlsEqual(url)
        self.assertEqual(officer.dbsformlogs.count(), 1)

        if self.is_full_browser_test:
            # Undo only works with Javascript at the moment
            self.click_dbs_sent_undo_button(officer)
            self.assertEqual(officer.dbsformlogs.count(), 0)
            self.assertUrlsEqual(url)


class ManageDbsPageWT(ManageDbsPageBase, WebTestBase):
    def click_dbs_sent_button(self, officer):
        self.submit('#id_send_{0}'.format(officer.id))

    def click_dbs_sent_undo_button(self, officer):
        raise NotImplementedError()


class ManageDbsPageSL(ManageDbsPageBase, SeleniumBase):
    def click_dbs_sent_button(self, officer):
        self.click('#id_send_{0}'.format(officer.id))
        self.wait_for_ajax()

    def click_dbs_sent_undo_button(self, officer):
        self.click('#id_undo_{0}'.format(officer.id))
        self.wait_for_ajax()
