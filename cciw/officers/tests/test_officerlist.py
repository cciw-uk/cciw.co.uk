import time
from datetime import date, timedelta

import xlrd
from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camp_factories
from cciw.cciwmain.tests.base import SiteSetupMixin
from cciw.officers.create import create_officer
from cciw.officers.models import Application
from cciw.officers.tests import factories
from cciw.officers.utils import camp_serious_slacker_list, officer_data_to_spreadsheet
from cciw.utils.spreadsheet import ExcelFormatter
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase


class TestCreate(TestBase):
    def test_create(self):
        user = create_officer("Joe", "Bloggs", "joebloggs@example.com")

        user = User.objects.get(id=user.id)
        assert user.is_staff
        assert len(mail.outbox) == 1
        assert user.last_login is None


class TestExport(TestBase):
    def test_export_no_application(self):
        """
        Test that the export data view generates an Excel file with all the data
        we expect if there is no application form.
        """
        camp = camp_factories.create_camp(officers=[officer := factories.create_officer()])
        first_names = [o.first_name for o in [officer]]

        assert Application.objects.all().count() == 0

        for i, inv in enumerate(camp.invitations.all()):
            inv.notes = f"Some notes {i}"
            inv.save()

        workbook = officer_data_to_spreadsheet(camp, ExcelFormatter()).to_bytes()

        assert workbook is not None
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)

        # Spot checks on different types of data
        # From User model
        assert wksh.cell(0, 0).value == "First name"
        assert wksh.cell(1, 0).value in first_names

        # From Invitation model
        assert wksh.cell(0, 3).value == "Notes"
        assert wksh.cell(1, 3).value.startswith("Some notes")

    def test_export_with_application(self):
        """
        Test that the export data view generates an Excel file with all the data
        we expect if there are application forms.
        """
        camp = camp_factories.create_camp(officers=[officer := factories.create_officer()])
        factories.create_application(year=camp.year, officer=officer, address_firstline="123 The Way")

        workbook = officer_data_to_spreadsheet(camp, ExcelFormatter()).to_bytes()

        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)

        # Check data from Application model
        assert wksh.cell(0, 4).value == "Address"
        assert "123 The Way" in wksh.col_values(4)


class TestSlackers(TestBase):
    def test_serious_slackers(self):
        officer1 = factories.create_officer()
        officer2 = factories.create_officer()
        camp1 = camp_factories.create_camp(year=date.today().year - 2, officers=[officer1, officer2])
        camp2 = camp_factories.create_camp(year=date.today().year - 1, officers=[officer1, officer2])

        # Officer 1 submitted an Application, but officer 2 did not
        app = officer1.applications.create(
            date_saved=camp1.start_date - timedelta(days=10),
            finished=True,
        )

        # Officer 1 submitted references, but officer 2 did not
        factories.create_complete_reference(app.referees[0])
        factories.create_complete_reference(app.referees[1])

        # Officer 1 got a DBS done, but officer 2 did not
        officer1.dbs_checks.create(
            dbs_number="123456",
            completed=camp1.start_date - timedelta(days=5),
        )

        serious_slackers = camp_serious_slacker_list(camp2)

        assert serious_slackers == [
            {
                "officer": officer2,
                "missing_application_forms": [camp1],
                "missing_references": [camp1],
                "missing_dbss": [camp1],
                "last_good_apps_year": None,
                "last_good_refs_year": None,
                "last_good_dbss_year": None,
            }
        ]


class TestOfficerListPage(SiteSetupMixin, SeleniumBase):
    def add_button_selector(self, officer):
        return f'[data-officer-id="{officer.id}"] [data-add-button]'

    def remove_button_selector(self, officer):
        return f'[data-officer-id="{officer.id}"] [data-remove-button]'

    def edit_button_selector(self, officer):
        return f'[data-officer-id="{officer.id}"] [data-edit-button]'

    def resend_email_button_selector(self, officer):
        return f'[data-officer-id="{officer.id}"] [data-email-button]'

    def test_add(self):
        camp = camp_factories.create_camp(
            leader=(leader := factories.create_officer()),
        )
        officer = factories.create_officer()
        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)

        # Check initial:
        assert officer not in camp.officers.all()
        assert not self.is_element_present(self.remove_button_selector(officer))
        self.assertTextPresent(officer.email)

        # Action:
        self.click(self.add_button_selector(officer))
        self.wait_for_ajax()

        # DB check:
        assert officer in camp.officers.all()
        # UI check:
        assert self.is_element_present(self.remove_button_selector(officer))
        self.assertTextPresent(officer.email)

    def test_remove(self):
        camp = camp_factories.create_camp(
            leader=(leader := factories.create_officer()),
            officers=[officer := factories.create_officer()],
        )

        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)

        # Check initial:
        assert officer in camp.officers.all()
        assert not self.is_element_present(self.add_button_selector(officer))
        self.assertTextPresent(officer.email)

        # Action:
        self.click(self.remove_button_selector(officer))
        self.wait_for_ajax()

        # DB check:
        assert officer not in camp.officers.all()
        # UI check:
        assert self.is_element_present(self.add_button_selector(officer))
        self.assertTextPresent(officer.email)

    def test_resend_email(self):
        camp = camp_factories.create_camp(
            leader=(leader := factories.create_officer()),
            officers=[officer := factories.create_officer()],
        )

        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)

        # Action:
        self.click(self.resend_email_button_selector(officer), expect_alert=True)
        self.accept_alert()
        self.wait_until(lambda *args: len(mail.outbox) > 0)
        (m,) = mail.outbox
        assert officer.first_name in m.body
        assert "https://" + settings.PRODUCTION_DOMAIN + "/officers/" in m.body

    def test_edit(self):
        camp = camp_factories.create_camp(
            leader=(leader := factories.create_officer()),
            officers=[officer := factories.create_officer()],
        )

        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)
        assert not self.is_element_displayed("#id_officer_save")

        self.click(self.edit_button_selector(officer))
        assert self.is_element_displayed("#id_officer_save")
        self.fill(
            {
                "#id_officer_first_name": "Altered",
                "#id_officer_last_name": "Name",
                "#id_officer_email": "alteredemail@somewhere.com",
                "#id_officer_notes": "A New Note",
            }
        )
        self.click("#id_officer_save")
        self.wait_for_ajax()

        # Test DB
        officer.refresh_from_db()
        assert officer.first_name == "Altered"
        assert officer.last_name == "Name"
        assert officer.email == "alteredemail@somewhere.com"
        invitation = camp.invitations.get(officer=officer)
        assert invitation.notes == "A New Note"

        # Test UI:
        assert not self.is_element_displayed("#id_officer_save")
        assert not self.is_element_displayed("#id_officer_first_name")
        self.assertTextPresent("alteredemail@somewhere.com")

    def test_edit_validation(self):
        camp = camp_factories.create_camp(
            leader=(leader := factories.create_officer()),
            officers=[officer := factories.create_officer()],
        )

        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)

        self.click(self.edit_button_selector(officer))
        self.fill({"#id_officer_email": "bademail"})
        self.click("#id_officer_save", expect_alert=True)

        # Test DB
        officer = User.objects.get(id=officer.id)
        assert officer.email != "bademail"

        # Test UI:
        self.accept_alert()
        assert self.is_element_displayed("#id_officer_save")

    def test_add_officer_button(self):
        camp = camp_factories.create_camp(leader=(leader := factories.create_officer()))
        self.officer_login(leader)
        self.get_url("cciw-officers-officer_list", camp_id=camp.url_id)
        self.click("#id_new_officer_btn")
        self.wait_for_ajax()
        time.sleep(5.0)
        assert self.is_element_displayed("#id_add_officer_popup")
        self.click("#id_popup_close_btn")
        self.wait_for_ajax()
        time.sleep(1.5)
        assert not self.is_element_displayed("#id_add_officer_popup")
        # Functionality of "New officer" popup is tested separately.


class TestNewOfficerPopup(SiteSetupMixin, WebTestBase):
    # This is implemented as a popup from the officer list that shows an iframe
    # hosting a separate page, making it easiest to test using WebTest on the
    # separate page.

    CONFIRM_BUTTON = "input[name=confirm]"

    def setUp(self):
        super().setUp()
        mail.outbox = []

    def get_page(self, camp):
        self.get_literal_url(reverse("cciw-officers-create_officer") + f"?camp_id={camp.id}")

    def test_permissions(self):
        camp = camp_factories.create_camp(leader=(leader := factories.create_officer()), future=True)
        self.get_page(camp)
        assert self.is_element_present("body.login")
        self.officer_login(leader)
        self.get_page(camp)
        assert not self.is_element_present("body.login")
        self.assertTextPresent("Enter details for officer")

    def _access_officer_list_page(self) -> Camp:
        camp = camp_factories.create_camp(leader=(leader := factories.create_officer()), future=True)
        self.officer_login(leader)
        self.get_page(camp)
        return camp

    def test_success(self):
        camp = self._access_officer_list_page()
        self.fill(
            {
                "#id_first_name": "Mary",
                "#id_last_name": "Andrews",
                "#id_email": "mary@andrews.com",
            }
        )
        self.submit("input[type=submit]")
        self._assert_created(camp)

    def test_duplicate_user(self):
        factories.create_officer(
            username="maryandrews", first_name="Mary", last_name="Andrews", email="mary@andrews.com"
        )
        self._access_officer_list_page()
        self.fill(
            {
                "#id_first_name": "Mary",
                "#id_last_name": "Andrews",
                "#id_email": "mary@andrews.com",
            }
        )
        self.submit("input[type=submit]")
        self.assertTextPresent("A user with that name and email address already exists")
        assert not self.is_element_present(self.CONFIRM_BUTTON)

    def test_duplicate_name(self):
        factories.create_officer(
            username="maryandrews", first_name="Mary", last_name="Andrews", email="mary@otheremail.com"
        )
        camp = self._access_officer_list_page()
        self.fill(
            {
                "#id_first_name": "Mary",
                "#id_last_name": "Andrews",
                "#id_email": "mary@andrews.com",
            }
        )
        self.submit("input[type=submit]")
        self.assertTextPresent("A user with that first name and last name already exists")
        self.submit(self.CONFIRM_BUTTON)
        self._assert_created(camp)

    def test_duplicate_email(self):
        factories.create_officer(
            username="mikeandrews", first_name="Mike", last_name="Andrews", email="mary@andrews.com"
        )
        camp = self._access_officer_list_page()
        self.fill(
            {
                "#id_first_name": "Mary",
                "#id_last_name": "Andrews",
                "#id_email": "mary@andrews.com",
            }
        )
        self.submit("input[type=submit]")
        self.assertTextPresent("A user with that email address already exists")
        self.submit(self.CONFIRM_BUTTON)
        self._assert_created(camp)

    def _assert_created(self, camp):
        u = User.objects.get(email="mary@andrews.com", first_name="Mary")
        assert u.first_name == "Mary"
        assert u.last_name == "Andrews"
        c = User.objects.filter(first_name="Mary", last_name="Andrews").count()
        username = "maryandrews" + (str(c) if c > 1 else "")

        assert u.username == username
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "Hi Mary" in m.body
        assert "https://" + settings.PRODUCTION_DOMAIN + "/officers/" in m.body
        assert u in camp.officers.all()
