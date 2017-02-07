from cciw.officers.tests.base import ApplicationSetupMixin
from cciw.utils.tests.webtest import WebTestBase, SeleniumBase
from django_functest import FuncBaseMixin

from .base import SECRETARY


class ManageCrbPageBase(ApplicationSetupMixin, FuncBaseMixin):

    def test_view_no_application_forms(self):
        camp = self.default_camp_1
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_crbs', camp.year)
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
        self.get_url('cciw-officers-manage_crbs', camp.year)
        self.assertTextAbsent('Needs application form')


class ManageCrbPageWT(ManageCrbPageBase, WebTestBase):
    pass


class ManageCrbPageSL(ManageCrbPageBase, SeleniumBase):
    def test_log_crb_sent(self):
        self.create_default_applications()
        camp = self.default_camp_1
        officer = self.officer1
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_crbs', camp.year)

        self.assertEqual(officer.crbformlogs.count(), 0)

        self.click('#id_send_{0}'.format(officer.id))
        self.wait_for_ajax()

        self.assertEqual(officer.crbformlogs.count(), 1)

        self.click('#id_undo_{0}'.format(officer.id))
        self.wait_for_ajax()

        self.assertEqual(officer.crbformlogs.count(), 0)
