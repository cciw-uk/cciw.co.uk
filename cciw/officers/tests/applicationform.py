from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.tests.references import OFFICER
from django.contrib.auth.models import User
from django.test import TestCase
from twill import commands as tc

class ApplicationFormView(TwillMixin, TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml']

    def _add_application(self):
        u = User.objects.get(username=OFFICER[0])
        c = Camp.objects.get(id=1)
        a = Application(officer=u, camp=c)
        a.save()
        return a

    def test_add_application(self):
        self._twill_login(OFFICER)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/add/"))
        tc.code(200)
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.submit(None)
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')

    def test_change_application(self):
        self._twill_login(OFFICER)
        a = self._add_application()
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 1)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/%s/" % a.id))
        tc.code(200)
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.submit(None)
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')
