from datetime import date, timedelta

from django.core import mail
from django.utils import timezone

from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.dbs import get_officers_with_dbs_info_for_camps
from cciw.officers.models import DBSActionLog, DBSActionLogType, DBSCheck
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase

from . import factories


class DbsInfoTests(TestBase):
    def setUp(self):
        super().setUp()
        self.camp = camp_factories.create_camp()
        self.year = self.camp.year
        self.officer_user = factories.create_officer()
        self.camp.invitations.create(officer=self.officer_user)

    def get_officer_with_dbs_info(self):
        camps = Camp.objects.filter(year=self.year)
        officers_and_dbs_info = get_officers_with_dbs_info_for_camps(camps, camps)
        relevant = [(o, c) for o, c in officers_and_dbs_info if o == self.officer_user]
        assert len(relevant) == 1
        return relevant[0]

    def test_requires_action_no_application_form(self):
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.requires_action

    def test_requires_action_with_application_form(self):
        factories.create_application(self.officer_user, year=self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.requires_action

    def test_can_register_received_dbs_form(self):
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.can_register_received_dbs_form
        factories.create_application(self.officer_user, year=self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.can_register_received_dbs_form

    def test_last_action_attributes(self):
        factories.create_application(self.officer_user, year=self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.last_dbs_form_sent is None
        assert dbs_info.last_leader_alert_sent is None

        # Now create an 'form sent' action log
        t1 = timezone.now()
        DBSActionLog.objects.create(officer=self.officer_user, created_at=t1, action_type=DBSActionLogType.FORM_SENT)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.last_dbs_form_sent is not None
        assert dbs_info.last_dbs_form_sent == t1

        # A leader alert action should not change last_dbs_form_sent
        t2 = timezone.now()
        DBSActionLog.objects.create(
            officer=self.officer_user, created_at=t2, action_type=DBSActionLogType.LEADER_ALERT_SENT
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.last_dbs_form_sent == t1

        # But we should now have last_leader_alert_sent
        assert dbs_info.last_leader_alert_sent == t2

    def test_can_check_dbs_online_default(self):
        factories.create_application(self.officer_user, year=self.year)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.can_check_dbs_online

    def test_can_check_dbs_online_application_form_dbs_number(self):
        # If we only have a DBS number from application form, we can't do online
        # check.
        factories.create_application(self.officer_user, year=self.year, dbs_number="00123")
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.update_enabled_dbs_number.number == "00123"
        assert dbs_info.update_enabled_dbs_number.previous_check_good is None
        assert not dbs_info.can_check_dbs_online

    def test_can_check_dbs_online_previous_check_dbs_number(self):
        application = factories.create_application(self.officer_user, year=self.year)
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(365 * 10),
            dbs_number="001234",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
            applicant_accepted=True,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.can_check_dbs_online
        assert dbs_info.update_enabled_dbs_number.number == "001234"
        assert dbs_info.update_enabled_dbs_number.previous_check_good

    def test_can_check_dbs_online_combined_info(self):
        # Application form indicates update-enabled DBS
        application = factories.create_application(self.officer_user, year=self.year, dbs_number="00123")

        # DBS check indicates good DBS, but don't know if it is
        # registered as update-enabled
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(365 * 10),
            dbs_number="00123",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=None,
            applicant_accepted=True,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()

        # We should be able to combine the above info:
        assert dbs_info.can_check_dbs_online
        assert dbs_info.update_enabled_dbs_number.number == "00123"
        assert dbs_info.update_enabled_dbs_number.previous_check_good

    def test_applicant_rejected_recent(self):
        application = factories.create_application(self.officer_user, year=self.year)
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(days=10),
            dbs_number="00123",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
            applicant_accepted=False,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.can_check_dbs_online
        assert dbs_info.applicant_rejected

    def test_applicant_rejected_old(self):
        application = factories.create_application(self.officer_user, year=self.year)
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(days=365 * 10),
            dbs_number="00123",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
            applicant_accepted=False,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.can_check_dbs_online
        assert dbs_info.applicant_rejected

    def test_can_check_dbs_online_previous_check_bad(self):
        application = factories.create_application(self.officer_user, year=self.year)
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(365 * 10),
            dbs_number="00123",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
            applicant_accepted=False,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert not dbs_info.can_check_dbs_online
        assert dbs_info.update_enabled_dbs_number.number == "00123"
        assert not dbs_info.update_enabled_dbs_number.previous_check_good

    def test_update_enabled_dbs_number(self):
        # Test that data from Application/DBSCheck is prioritised by date
        application = factories.create_application(self.officer_user, year=self.year, dbs_number="00123")
        self.officer_user.dbs_checks.create(
            completed_on=application.saved_on - timedelta(365 * 10),
            dbs_number="00456",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        # Application form data should win because it is more recent
        assert dbs_info.update_enabled_dbs_number.number == "00123"
        assert dbs_info.update_enabled_dbs_number.previous_check_good is None


class ManageDbsPageSL(SeleniumBase):
    def setUp(self):
        super().setUp()
        self.officer_user = factories.create_officer()
        self.camp = camp_factories.create_camp(leader=factories.create_officer(), officers=[self.officer_user])
        self.year = self.camp.year
        self.dbs_officer = factories.create_dbs_officer()

    def assertElementText(self, css_selector, text):
        assert self.get_element_inner_text(css_selector).strip().replace("\u00A0", " ") == text

    def test_view_no_application_forms(self):
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.assertCode(200)
        self.assertTextPresent(f"Manage DBSs {self.year} | CCiW Officers", within="title")

        officers = [i.officer for i in self.camp.invitations.all()]
        assert len(officers) != 0
        for officer in officers:
            # Sanity check assumptions
            assert officer.applications.count() == 0

            # Actual test
            self.assertTextPresent(officer.first_name)
            self.assertTextPresent(officer.last_name)

        self.assertTextPresent("Needs application form")

    def test_view_with_application_forms(self):
        factories.create_application(self.officer_user, year=self.year)
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.assertTextAbsent("Needs application form")

    def test_log_dbs_sent(self):
        factories.create_application(self.officer_user, year=self.year)
        officer = self.officer_user
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)

        assert officer.dbsactionlogs.count() == 0

        self.click_dbs_sent_button(officer)
        self.wait_for_ajax()
        assert officer.dbsactionlogs.count() == 1
        assert officer.dbsactionlogs.get().user.username == self.dbs_officer.username

        self.assertElementText(f'[data-officer-id="{officer.id}"] [data-last-dbs-form-sent]', "0 minutes ago")

        self.click_dbs_sent_undo_button(officer)
        self.wait_for_ajax()
        assert officer.dbsactionlogs.count() == 0
        self.assertElementText(f'[data-officer-id="{officer.id}"] [data-last-dbs-form-sent]', "No record")

    def test_alert_leaders(self):
        factories.create_application(self.officer_user, year=self.year, dbs_check_consent=False)
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.assertTextPresent("Officer does not consent")
        self.assertElementText(f'[data-officer-id="{self.officer_user.id}"] [data-last-leader-alert-sent]', "No record")
        self.click_alert_leaders_button(self.officer_user)
        self.assertTextPresent("Report DBS problem to leaders")
        self.click('input[name="send"]', scroll=False)
        self.wait_for_dialog_close()
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "Dear camp leaders" in m.body
        assert f"{self.officer_user.full_name} indicated that they do NOT\nconsent to having a DBS check done" in m.body

        assert self.dbs_officer.dbsactions_performed.count() == 1
        assert self.dbs_officer.dbsactions_performed.get().action_type == DBSActionLogType.LEADER_ALERT_SENT

        self.assertElementText(
            f'[data-officer-id="{self.officer_user.id}"] [data-last-leader-alert-sent]', "0 minutes ago"
        )

    def wait_for_dialog_close(self):
        self.wait_until(lambda _: not self.is_element_displayed("dialog"))
        self.wait_for_ajax()

    def test_request_dbs_form_sent(self):
        factories.create_application(self.officer_user, year=self.year)
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.assertElementText(f'[data-officer-id="{self.officer_user.id}"] [data-last-form-request-sent]', "No record")
        self.click_request_dbs_form_button(self.officer_user)
        self.assertTextPresent(f"Ask for DBS form to be sent to {self.officer_user.full_name}", within="dialog")
        self.click('input[name="send"]')
        self.wait_for_dialog_close()
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert f"{self.officer_user.full_name} needs a new DBS check" in m.body

        assert self.dbs_officer.dbsactions_performed.count() == 1
        assert self.dbs_officer.dbsactions_performed.get().action_type == DBSActionLogType.REQUEST_FOR_DBS_FORM_SENT

        self.assertElementText(
            f'[data-officer-id="{self.officer_user.id}"] [data-last-form-request-sent]', "0 minutes ago"
        )

    def test_register_received_dbs(self):
        factories.create_application(self.officer_user, year=self.year)
        assert self.officer_user.dbs_checks.all().count() == 0
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.click_register_received_button(self.officer_user)
        self.assertTextPresent(f"Add DBS check for {self.officer_user.full_name}", within="dialog")
        self.fill(
            {
                "#id_dbs_number": "1234",
                "#id_completed_on": date.today().strftime("%Y-%m-%d"),
            }
        )
        self.click('input[name="save"]')
        self.wait_for_dialog_close()

        dbs_checks = list(self.officer_user.dbs_checks.all())
        assert len(dbs_checks) == 1
        dbs_check = dbs_checks[0]
        assert dbs_check.dbs_number == "1234"

        # DBS received - no need to have any action buttons.
        assert not self.is_element_present(self.register_received_button_selector(self.officer_user))

    def test_dbs_checked_online(self):
        """
        Test the "DBS checked online" action and flow
        """
        factories.create_application(self.officer_user, year=self.year)

        # Create old DBS check
        assert self.officer_user.dbs_checks.count() == 0
        self.officer_user.dbs_checks.create(
            dbs_number="00123400001",
            completed_on=date(1990, 1, 1),
            requested_by=DBSCheck.RequestedBy.CCIW,
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
        )
        today = date.today()

        # Use the DBS page
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.click_dbs_checked_online_button(self.officer_user)
        # Should be filled out with everything needed.
        self.click('input[name="save"]')
        self.wait_for_dialog_close()

        # Check created DBS:
        assert self.officer_user.dbs_checks.count() == 2
        dbs_check = self.officer_user.dbs_checks.all().order_by("-completed_on")[0]

        # Should have copied other info from old DBS check automatically.
        assert dbs_check.dbs_number == "00123400001"
        assert dbs_check.check_type == DBSCheck.CheckType.ONLINE
        assert dbs_check.completed_on == today
        assert dbs_check.requested_by == DBSCheck.RequestedBy.CCIW
        assert dbs_check.registered_with_dbs_update

        # Check done - no need for any action buttons
        assert not self.is_element_present(self.dbs_checked_online_button_selector(self.officer_user))

    def register_received_button_selector(self, officer):
        return f'tr[data-officer-id="{officer.id}"] button[name="register_received_dbs"]'

    def dbs_checked_online_button_selector(self, officer):
        return f'tr[data-officer-id="{officer.id}"] button[name="dbs_checked_online"]'

    def click_dbs_sent_button(self, officer):
        self.click(f'tr[data-officer-id="{officer.id}"] button[name="mark_sent"]')
        self.wait_for_ajax()

    def click_dbs_sent_undo_button(self, officer):
        self.click(f'tr[data-officer-id="{officer.id}"] button[name="undo_last_mark_sent"]')
        self.wait_for_ajax()

    def click_alert_leaders_button(self, officer):
        self.click(f'tr[data-officer-id="{officer.id}"] button[name="alert_leaders"]')
        self.wait_for_ajax()

    def click_request_dbs_form_button(self, officer):
        self.click(f'tr[data-officer-id="{officer.id}"] button[name="request_form_to_be_sent"]')
        self.wait_for_ajax()

    def click_register_received_button(self, officer):
        self.click(self.register_received_button_selector(officer))
        self.wait_for_ajax()

    def click_dbs_checked_online_button(self, officer):
        self.click(self.dbs_checked_online_button_selector(officer))
        self.wait_for_ajax()
