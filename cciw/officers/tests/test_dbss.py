import time
from datetime import date, timedelta

from django.core import mail
from django.utils import timezone
from django_functest import FuncBaseMixin

from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.base import factories as camp_factories
from cciw.officers.dbs import get_officers_with_dbs_info_for_camps
from cciw.officers.models import DBSActionLog, DBSCheck
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase

from .base import factories


class DbsInfoTests(TestBase):
    def setUp(self):
        super().setUp()
        self.camp = camp_factories.create_camp()
        self.year = self.camp.year
        self.officer_user = factories.create_officer()
        self.camp.invitations.create(officer=self.officer_user)

    def get_officer_with_dbs_info(self):
        camps = Camp.objects.filter(year=self.year)
        officers_and_dbs_info = get_officers_with_dbs_info_for_camps(camps)
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
        DBSActionLog.objects.create(officer=self.officer_user, created_at=t1, action_type=DBSActionLog.ACTION_FORM_SENT)
        officer, dbs_info = self.get_officer_with_dbs_info()
        assert dbs_info.last_dbs_form_sent is not None
        assert dbs_info.last_dbs_form_sent == t1

        # A leader alert action should not change last_dbs_form_sent
        t2 = timezone.now()
        DBSActionLog.objects.create(
            officer=self.officer_user, created_at=t2, action_type=DBSActionLog.ACTION_LEADER_ALERT_SENT
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
            completed=application.date_saved - timedelta(365 * 10),
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
            completed=application.date_saved - timedelta(365 * 10),
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
            completed=application.date_saved - timedelta(days=10),
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
            completed=application.date_saved - timedelta(days=365 * 10),
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
            completed=application.date_saved - timedelta(365 * 10),
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
            completed=application.date_saved - timedelta(365 * 10),
            dbs_number="00456",
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
        )
        officer, dbs_info = self.get_officer_with_dbs_info()
        # Application form data should win because it is more recent
        assert dbs_info.update_enabled_dbs_number.number == "00123"
        assert dbs_info.update_enabled_dbs_number.previous_check_good is None


class ManageDbsPageBase(FuncBaseMixin):
    def setUp(self):
        super().setUp()
        self.camp = camp_factories.create_camp(leader=factories.create_leader())
        self.year = self.camp.year
        self.officer_user = factories.create_officer()
        self.camp.invitations.create(officer=self.officer_user)
        self.dbs_officer = factories.create_dbs_officer()

    def test_view_no_application_forms(self):
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        self.assertCode(200)
        self.assertTextPresent(f"Manage DBSs {self.year} | CCiW Officers")

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
        url = self.current_url

        assert officer.dbsactionlogs.count() == 0

        self.click_dbs_sent_button(officer)
        # should be on same page
        self.assertUrlsEqual(url)
        assert officer.dbsactionlogs.count() == 1
        assert officer.dbsactionlogs.get().user.username == self.dbs_officer.username

        if self.is_full_browser_test:
            self.assertElementText(f"#id_last_dbs_form_sent_{officer.id}", "Just now")

        if self.is_full_browser_test:
            # Undo only works with Javascript at the moment
            self.click_dbs_sent_undo_button(officer)
            assert officer.dbsactionlogs.count() == 0
            self.assertUrlsEqual(url)

    def test_alert_leaders(self):
        factories.create_application(self.officer_user, year=self.year, dbs_check_consent=False)
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        url = self.current_url
        self.assertTextPresent("Officer does not consent")
        assert self.get_element_text(f"#id_last_leader_alert_sent_{self.officer_user.id}").strip() == "No record"
        self.click_alert_leaders_button(self.officer_user)
        self.assertTextPresent("Report DBS problem to leaders")
        self.submit('input[name="send"]')
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "Dear camp leaders" in m.body
        assert f"{self.officer_user.full_name} indicated that they do NOT\nconsent to having a DBS check done" in m.body

        assert self.dbs_officer.dbsactions_performed.count() == 1
        assert self.dbs_officer.dbsactions_performed.get().action_type == DBSActionLog.ACTION_LEADER_ALERT_SENT

        self.handle_closed_window()
        self.assertUrlsEqual(url)

        assert (
            self.get_element_text(f"#id_last_leader_alert_sent_{self.officer_user.id}").strip().replace("\u00A0", " ")
            == "0 minutes ago"
        )

    def test_request_dbs_form_sent(self):
        factories.create_application(self.officer_user, year=self.year)
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        url = self.current_url
        assert self.get_element_text(f"#id_last_form_request_sent_{self.officer_user.id}").strip() == "No record"
        self.click_request_dbs_form_button(self.officer_user)
        self.assertTextPresent(f"Ask for DBS form to be sent to {self.officer_user.full_name}")
        self.submit('input[name="send"]')
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert f"{self.officer_user.full_name} needs a new DBS check" in m.body

        assert self.dbs_officer.dbsactions_performed.count() == 1
        assert self.dbs_officer.dbsactions_performed.get().action_type == DBSActionLog.ACTION_REQUEST_FOR_DBS_FORM_SENT

        self.handle_closed_window()
        self.assertUrlsEqual(url)

        assert (
            self.get_element_text(f"#id_last_form_request_sent_{self.officer_user.id}").strip().replace("\u00A0", " ")
            == "0 minutes ago"
        )

    def test_register_received_dbs(self):
        factories.create_application(self.officer_user, year=self.year)
        assert self.officer_user.dbs_checks.all().count() == 0
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        url = self.current_url
        self.click_register_received_button(self.officer_user)
        self.fill(
            {
                "#id_dbs_number": "1234",
                "#id_completed": date.today().strftime("%Y-%m-%d"),
            }
        )
        self.submit('input[name="_save"]')

        dbs_checks = list(self.officer_user.dbs_checks.all())
        assert len(dbs_checks) == 1
        dbs_check = dbs_checks[0]
        assert dbs_check.dbs_number == "1234"

        self.handle_closed_window()
        self.assertUrlsEqual(url)

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
            completed=date(1990, 1, 1),
            requested_by=DBSCheck.RequestedBy.CCIW,
            check_type=DBSCheck.CheckType.FORM,
            registered_with_dbs_update=True,
        )
        today = date.today()

        # Use the DBS page
        self.officer_login(self.dbs_officer)
        self.get_url("cciw-officers-manage_dbss", self.year)
        url = self.current_url
        self.click_dbs_checked_online_button(self.officer_user)
        # Should be filled out with everything needed.
        self.submit('input[name="_save"]')

        # Check created DBS:
        assert self.officer_user.dbs_checks.count() == 2
        dbs_check = self.officer_user.dbs_checks.all().order_by("-completed")[0]

        # Should have copied other info from old DBS check automatically.
        assert dbs_check.dbs_number == "00123400001"
        assert dbs_check.check_type == DBSCheck.CheckType.ONLINE
        assert dbs_check.completed == today
        assert dbs_check.requested_by == DBSCheck.RequestedBy.CCIW
        assert dbs_check.registered_with_dbs_update

        self.handle_closed_window()
        self.assertUrlsEqual(url)
        # Check done - no need for any action buttons
        assert not self.is_element_present(self.dbs_checked_online_button_selector(self.officer_user))

    def click_register_received_button(self, officer):
        self.submit(self.register_received_button_selector(officer))

    def register_received_button_selector(self, officer):
        return f"#id_register_received_dbs_{officer.id}"

    def click_dbs_checked_online_button(self, officer):
        self.submit(self.dbs_checked_online_button_selector(officer))

    def dbs_checked_online_button_selector(self, officer):
        return f"#id_dbs_checked_online_{officer.id}"


class ManageDbsPageWT(ManageDbsPageBase, WebTestBase):
    def handle_closed_window(self):
        # with no javascript, instead of popups and
        # closing windows, we get redirects which
        # handle everything.
        pass

    def click_dbs_sent_button(self, officer):
        self.submit(f"#id_send_{officer.id}")

    def click_dbs_sent_undo_button(self, officer):
        raise NotImplementedError()

    def click_alert_leaders_button(self, officer):
        self.submit(f"#id_alert_leaders_{officer.id}")

    def click_request_dbs_form_button(self, officer):
        self.submit(f"#id_request_form_to_be_sent_{officer.id}")


class ManageDbsPageSL(ManageDbsPageBase, SeleniumBase):
    def handle_closed_window(self):
        # Previous page opened in new window. It is closed now...
        assert len(self._driver.window_handles) == 1
        # but we still need to switch back.
        self.switch_window()
        time.sleep(1)
        self.wait_for_ajax()

    def click_dbs_sent_button(self, officer):
        self.click(f"#id_send_{officer.id}")
        self.wait_for_ajax()

    def click_dbs_sent_undo_button(self, officer):
        self.click(f"#id_undo_{officer.id}")
        self.wait_for_ajax()

    def click_alert_leaders_button(self, officer):
        self.click(f"#id_alert_leaders_{officer.id}")
        self.switch_window()
        self.wait_until_loaded("body")

    def click_request_dbs_form_button(self, officer):
        self.click(f"#id_request_form_to_be_sent_{officer.id}")
        self.switch_window()
        self.wait_until_loaded("body")

    def click_register_received_button(self, officer):
        self.click(self.register_received_button_selector(officer))
        self.switch_window()
        self.wait_until_loaded("body")

    def click_dbs_checked_online_button(self, officer):
        self.click(self.dbs_checked_online_button_selector(officer))
        self.switch_window()
        self.wait_until_loaded("body")
