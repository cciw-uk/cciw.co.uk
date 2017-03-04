from datetime import date

from django.utils import timezone
from django.core import mail
from django_functest import FuncBaseMixin

from cciw.cciwmain.models import Camp
from cciw.officers.models import DBSActionLog
from cciw.officers.views import get_officers_with_dbs_info_for_camps
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase

from .base import SECRETARY, CreateApplicationMixin, OfficersSetupMixin, SimpleOfficerSetupMixin


class DbsInfoTests(SimpleOfficerSetupMixin, CreateApplicationMixin, TestBase):
    def setUp(self):
        super(DbsInfoTests, self).setUp()
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

    def test_can_register_received_dbs_form(self):
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertFalse(dbs_info.can_register_received_dbs_form)
        self.create_application(self.officer_user, self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertTrue(dbs_info.can_register_received_dbs_form)

    def test_last_action_attributes(self):
        self.create_application(self.officer_user, self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertEqual(dbs_info.last_dbs_form_sent, None)
        self.assertEqual(dbs_info.last_leader_alert_sent, None)

        # Now create an 'form sent' action log
        t1 = timezone.now()
        DBSActionLog.objects.create(officer=self.officer_user,
                                    timestamp=t1,
                                    action_type=DBSActionLog.ACTION_FORM_SENT)
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertNotEqual(dbs_info.last_dbs_form_sent, None)
        self.assertEqual(dbs_info.last_dbs_form_sent, t1)

        # A leader alert action should not change last_dbs_form_sent
        t2 = timezone.now()
        DBSActionLog.objects.create(officer=self.officer_user,
                                    timestamp=t2,
                                    action_type=DBSActionLog.ACTION_LEADER_ALERT_SENT)
        officer, dbs_info = self.get_officer_with_dbs_info()
        self.assertEqual(dbs_info.last_dbs_form_sent, t1)

        # But we should now have last_leader_alert_sent
        self.assertEqual(dbs_info.last_leader_alert_sent, t2)


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

        self.assertEqual(officer.dbsactionlogs.count(), 0)

        self.click_dbs_sent_button(officer)
        # should be on same page
        self.assertUrlsEqual(url)
        self.assertEqual(officer.dbsactionlogs.count(), 1)
        self.assertEqual(officer.dbsactionlogs.get().user.username,
                         SECRETARY[0])

        if self.is_full_browser_test:
            self.assertElementText('#id_last_dbs_form_sent_{0}'.format(officer.id),
                                   'Just now')

        if self.is_full_browser_test:
            # Undo only works with Javascript at the moment
            self.click_dbs_sent_undo_button(officer)
            self.assertEqual(officer.dbsactionlogs.count(), 0)
            self.assertUrlsEqual(url)

    def test_alert_leaders(self):
        self.create_application(self.officer_user, self.year,
                                overrides={'dbs_check_consent': False})
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', self.year)
        url = self.current_url
        self.assertTextPresent('Officer does not consent')
        self.click_alert_leaders_button(self.officer_user)
        self.assertTextPresent("Report DBS problem to leaders")
        self.submit('input[name="send"]')
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertIn("Dear camp leaders",
                      m.body)
        self.assertIn("{0} {1} indicated that they do NOT\nconsent to having a DBS check done"
                      .format(self.officer_user.first_name,
                              self.officer_user.last_name),
                      m.body)
        if self.is_full_browser_test:
            # Previous page opened in new window. It is closed now,
            # but we still need to switch back.
            self.switch_window()
        self.assertUrlsEqual(url)
        self.assertEqual(self.secretary.dbsactions_performed.count(), 1)
        self.assertEqual(self.secretary.dbsactions_performed.get().action_type,
                         DBSActionLog.ACTION_LEADER_ALERT_SENT)

    def test_register_received_dbs(self):
        self.create_application(self.officer_user, self.year)
        self.assertEqual(self.officer_user.dbs_checks.all().count(), 0)
        self.officer_login(SECRETARY)
        self.get_url('cciw-officers-manage_dbss', self.year)
        url = self.current_url
        self.click_register_received_button(self.officer_user)
        self.fill({'#id_dbs_number': '1234',
                   '#id_completed': date.today().strftime('%Y-%m-%d'),
                   })
        self.submit('input[name="_save"]')

        # Should get redirected back
        self.assertUrlsEqual(url)
        dbs_checks = list(self.officer_user.dbs_checks.all())
        self.assertEqual(len(dbs_checks), 1)
        dbs_check = dbs_checks[0]
        self.assertEqual(dbs_check.dbs_number, '1234')

    def click_register_received_button(self, officer):
        self.submit('#id_register_received_dbs_{0}'.format(officer.id))


class ManageDbsPageWT(ManageDbsPageBase, WebTestBase):
    def click_dbs_sent_button(self, officer):
        self.submit('#id_send_{0}'.format(officer.id))

    def click_dbs_sent_undo_button(self, officer):
        raise NotImplementedError()

    def click_alert_leaders_button(self, officer):
        self.submit('#id_alert_leaders_{0}'.format(officer.id))


class ManageDbsPageSL(ManageDbsPageBase, SeleniumBase):
    def click_dbs_sent_button(self, officer):
        self.click('#id_send_{0}'.format(officer.id))
        self.wait_for_ajax()

    def click_dbs_sent_undo_button(self, officer):
        self.click('#id_undo_{0}'.format(officer.id))
        self.wait_for_ajax()

    def click_alert_leaders_button(self, officer):
        self.click('#id_alert_leaders_{0}'.format(officer.id))
        self.switch_window()
        self.wait_until_loaded('body')
