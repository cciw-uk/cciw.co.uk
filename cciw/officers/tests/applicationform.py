from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.tests.references import OFFICER
from django.contrib.auth.models import User
from django.core import mail
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
#        tc.find('Save and continue editing')
#        tc.notfind('Save and add another')
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.submit('_save')
        tc.url('officers/applications/$')
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')

    def test_change_application(self):
        self._twill_login(OFFICER)
        a = self._add_application()
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 1)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/%s/" % a.id))
        tc.code(200)
#        tc.find('Save and continue editing')
#        tc.notfind('Save and add another')
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.submit('_save')
        tc.url('officers/applications/$')
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')

    def test_finish_incomplete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self._twill_login(OFFICER)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/add/"))
        tc.code(200)
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'finished', 'on')
        tc.submit('_save')
        tc.url('admin/officers/application/add/$')
        tc.find("Please correct the errors below")
        tc.find("form-row errors full_name")
        self.assertEqual(u.application_set.count(), 0) # shouldn't have been saved

    def test_finish_complete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self._twill_login(OFFICER)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/add/"))
        tc.code(200)
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'finished', 'on')
        tc.formvalue('1', 'full_name', 'x')
        tc.formvalue('1', 'full_maiden_name', 'x')
        tc.formvalue('1', 'birth_date', '2000-01-01')
        tc.formvalue('1', 'birth_place', 'x')
        tc.formvalue('1', 'address_firstline', 'x')
        tc.formvalue('1', 'address_town', 'x')
        tc.formvalue('1', 'address_county', 'x')
        tc.formvalue('1', 'address_postcode', 'x')
        tc.formvalue('1', 'address_country', 'x')
        tc.formvalue('1', 'address_tel', 'x')
        tc.formvalue('1', 'address_mobile', 'x')
        tc.formvalue('1', 'address_since', '2008/01')
        tc.formvalue('1', 'address_email', 'foo@foo.com')
        tc.formvalue('1', 'address2_from', '2008/01')
        tc.formvalue('1', 'address2_to', '2008/01')
        tc.formvalue('1', 'address2_address', 'x')
        tc.formvalue('1', 'address3_from', '2008/01')
        tc.formvalue('1', 'address3_to', '2008/01')
        tc.formvalue('1', 'address3_address', 'x')
        tc.formvalue('1', 'christian_experience', 'x')
        tc.formvalue('1', 'youth_experience', 'x')
        tc.formvalue('1', 'youth_work_declined_details', 'x')
        tc.formvalue('1', 'illness_details', 'x')
        tc.formvalue('1', 'employer1_name', 'x')
        tc.formvalue('1', 'employer1_from', '2008/01')
        tc.formvalue('1', 'employer1_to', '2008/01')
        tc.formvalue('1', 'employer1_job', 'x')
        tc.formvalue('1', 'employer1_leaving', 'x')
        tc.formvalue('1', 'employer2_name', 'x')
        tc.formvalue('1', 'employer2_from', '2008/01')
        tc.formvalue('1', 'employer2_to', '2008/01')
        tc.formvalue('1', 'employer2_job', 'x')
        tc.formvalue('1', 'employer2_leaving', 'x')
        tc.formvalue('1', 'referee1_name', 'x')
        tc.formvalue('1', 'referee1_address', 'x')
        tc.formvalue('1', 'referee1_tel', 'x')
        tc.formvalue('1', 'referee1_mobile', 'x')
        tc.formvalue('1', 'referee1_email', 'foo1@foo1.com')
        tc.formvalue('1', 'referee2_name', 'x')
        tc.formvalue('1', 'referee2_address', 'x')
        tc.formvalue('1', 'referee2_tel', 'x')
        tc.formvalue('1', 'referee2_mobile', 'x')
        tc.formvalue('1', 'referee2_email', 'foo2@foo2.com')
        tc.formvalue('1', 'crime_details', 'x')
        tc.formvalue('1', 'court_details', 'x')
        tc.formvalue('1', 'concern_details', 'x')
        tc.formvalue('1', 'youth_work_declined', '2')
        tc.formvalue('1', 'relevant_illness', '2')
        tc.formvalue('1', 'crime_declaration', '2')
        tc.formvalue('1', 'court_declaration', '2')
        tc.formvalue('1', 'concern_declaration', '2')
        tc.formvalue('1', 'allegation_declaration', '2')
        tc.formvalue('1', 'crb_check_consent', '2')

        tc.submit('_save')
        tc.url('officers/applications/$')

        self.assertEqual(u.application_set.count(), 1)

        # There should be two emails in outbox, one to officer, one to
        # leader.  This assumes that there is a leader for the camp,
        # and it is associated with a User object.
        a = u.application_set.all()[0]
        self.assertEqual(a.camp.leaders.count(), 1)
        l = a.camp.leaders.all()[0]
        self.assertEqual(l.users.count(), 1)
        self.assertEqual(len(mail.outbox), 2)
