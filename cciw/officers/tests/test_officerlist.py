from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
import xlrd

from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.officers.create import create_officer
from cciw.officers.models import Application
from cciw.officers.tests.base import ApplicationSetupMixin
from cciw.officers.utils import officer_data_to_spreadsheet, camp_serious_slacker_list
from cciw.utils.spreadsheet import ExcelFormatter

User = get_user_model()


class TestCreate(TestCase):

    def test_create(self):
        user = create_officer("Joe", "Bloggs", "joebloggs@gmail.com")

        user = User.objects.get(id=user.id)
        self.assertTrue(user.is_staff)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(user.last_login, None)


class TestExport(ApplicationSetupMixin, TestCase):

    def test_export_no_application(self):
        """
        Test that the export data view generates an Excel file with all the data
        we expect if there is no application form.
        """
        c = Camp.objects.get(year=2000, number=1)
        officers = list(c.officers.all())
        first_names = [o.first_name for o in officers]

        # In this test, delete completed applications, so we can test what
        # happens with no application.
        Application.objects.all().delete()

        for i, inv in enumerate(c.invitations.all()):
            inv.notes = "Some notes %s" % i
            inv.save()

        workbook = officer_data_to_spreadsheet(c, ExcelFormatter())

        self.assertTrue(workbook is not None)
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)

        # Spot checks on different types of data
        # From User model
        self.assertEqual(wksh.cell(0, 0).value, "First name")
        self.assertTrue(wksh.cell(1, 0).value in first_names)

        # From Invitation model
        self.assertEqual(wksh.cell(0, 3).value, "Notes")
        self.assertTrue(wksh.cell(1, 3).value.startswith('Some notes'))

    def test_export_with_application(self):
        """
        Test that the export data view generates an Excel file with all the data
        we expect if there are application forms.
        """
        camp = self.default_camp_1

        # Data from setup
        u = self.officer1
        app = self.application1
        assert app.officer == u

        workbook = officer_data_to_spreadsheet(camp, ExcelFormatter())

        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)

        # Check data from Application model
        self.assertEqual(wksh.cell(0, 4).value, "Address")
        self.assertTrue(app.address_firstline in wksh.col_values(4))


class TestSlackers(BasicSetupMixin, TestCase):

    def test_serious_slackers(self):
        camp1 = self.default_camp_1
        camp2 = self.default_camp_2

        officer1 = User.objects.create(username="joe",
                                       email="joe@example.com")
        officer2 = User.objects.create(username="mary",
                                       email="mary@example.com")

        camp1.invitations.create(officer=officer1)
        camp1.invitations.create(officer=officer2)

        camp2.invitations.create(officer=officer1)
        camp2.invitations.create(officer=officer2)

        # Officer 1 submitted an Application, but officer 2 did not
        app = officer1.applications.create(
            date_submitted=camp1.start_date - timedelta(days=10),
            finished=True,
        )

        # Officer 1 submitted references, but officer 2 did not
        ref1, ref2 = app.references
        ref1.received = True
        ref1.save()
        ref2.received = True
        ref2.save()

        # Officer 1 got a CRB done, but officer 2 did not
        officer1.crb_applications.create(
            crb_number="123456",
            completed=camp1.start_date - timedelta(days=5),
        )

        serious_slackers = camp_serious_slacker_list(camp2)

        self.assertEqual(
            serious_slackers,
            [{'officer': officer2,
              'missing_application_forms': [camp1],
              'missing_references': [camp1],
              'missing_crbs': [camp1],
              'last_good_apps_year': None,
              'last_good_refs_year': None,
              'last_good_crbs_year': None,
              }])
