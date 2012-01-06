from django.contrib.auth.models import User
from django.test import TestCase
import xlrd

from cciw.cciwmain.models import Camp
from cciw.officers.models import Invitation, Application
from cciw.officers.tests.references import OFFICER, LEADER
from cciw.officers.utils import officer_data_to_spreadsheet
from cciw.utils.spreadsheet import ExcelFormatter


class TestExport(TestCase):

    fixtures = ['basic.json', 'officers_users.json', 'references.json']

    def test_export_no_application(self):
        """
        Test that the export data view generates an Excel file with all the data
        we expect if there is no application form.
        """
        c = Camp.objects.get(pk=1)
        officers = list(c.officers.all())
        first_names = [o.first_name for o in officers]

        # In this test, delete completed applications, so we can test what
        # happens with no application.
        Application.objects.all().delete()

        for i, inv in enumerate(c.invitation_set.all()):
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
        c = Camp.objects.get(pk=1)
        officers = list(c.officers.all())

        # Data from fixtures
        u = User.objects.get(pk=2)
        app = Application.objects.get(pk=1)
        assert app.officer == u

        workbook = officer_data_to_spreadsheet(c, ExcelFormatter())

        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)

        # Check data from Application model
        self.assertEqual(wksh.cell(0, 4).value, "Address")
        self.assertTrue(app.address_firstline in wksh.col_values(4))
