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

    def test_references(self):
        app1 = Application.objects.get(id=1)
        self.assertEqual(app1.references[0], app1.reference_set.get(referee_number=1))
        self.assertEqual(app1.references[1], app1.reference_set.get(referee_number=2))

        app2 = Application.objects.get(id=2)
        self.assertEqual(app2.references[0], None)
        self.assertEqual(app2.references[1], app2.reference_set.get(referee_number=2))

        app3 = Application.objects.get(id=3)
        self.assertEqual(app3.references[0], None)
        self.assertEqual(app3.references[1], None)


