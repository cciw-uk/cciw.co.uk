from django.test import TestCase
from cciw.officers.models import Application

from references import OFFICER_USERNAME 

class ApplicationModel(TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']

    def test_referees_get(self):
        """Tests the Application.referees getter utility"""
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        self.assertEqual(app.referees[0].name, app.referee1_name)
        self.assertEqual(app.referees[1].name, app.referee2_name)
        self.assertEqual(app.referees[0].address, app.referee1_address)
        self.assertEqual(app.referees[0].tel, app.referee1_tel)
        self.assertEqual(app.referees[0].mobile, app.referee1_mobile)
        self.assertEqual(app.referees[0].email, app.referee1_email)

    def test_referees_get_badattr(self):
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        self.assertRaises(AttributeError, lambda: app.references[0].badattr)

    def test_referees_set(self):
        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        app.referees[0].name = "A new name"
        self.assertEqual(app.referee1_name, "A new name")

    def test_referees_set_extra_attrs(self):
        """Tests that we can set and retrieve additional attributes,
        not just ones defined as part of Application model"""

        app = Application.objects.filter(officer__username=OFFICER_USERNAME)[0]
        app.referees[0].some_extra_attr = "Hello"
        self.assertEqual(app.referees[0].some_extra_attr, "Hello")
