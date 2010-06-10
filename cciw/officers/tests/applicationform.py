from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.tests.references import OFFICER, LEADER
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from twill import commands as tc
import datetime

class ApplicationFormView(TwillMixin, TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml']

    def setUp(self):
        # make sure camp 1 has end date in future, otherwise
        # we won't be able to save
        c = Camp.objects.get(id=1)
        c.end_date = datetime.date.today() + datetime.timedelta(100)
        c.save()

        super(ApplicationFormView, self).setUp()

    def _add_application(self):
        u = User.objects.get(username=OFFICER[0])
        c = Camp.objects.get(id=1)
        a = Application(officer=u, camp=c, address_email=u.email)
        a.save()
        return a

    def _finish_application_form(self):
        # A full set of values that pass validation.
        tc.formvalue('1', 'camp', '1')
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
        tc.formvalue('1', 'finished', 'on')

    def _get_application_form_emails(self):
        return [e for e in mail.outbox if "CCIW application form" in e.subject]

    def _get_email_change_emails(self):
        return [e for e in mail.outbox if "Email change" in e.subject]

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

    def test_add_application_leader(self):
        # Test that we don't get an error if a leader is using it, and forgets
        # to do fill out the 'officer' box.
        u = User.objects.get(username=LEADER[0])
        self.assertEqual(u.application_set.count(), 0)
        self._twill_login(LEADER)
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/add/"))
        tc.code(200)
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

    def test_change_email_address(self):
        # When submitted email address is different from the one stored against
        # the user, an e-mail should be sent with a link to update the stored
        # e-mail address

        # This is a 'story' test, really, not a unit test, because we want to
        # check several different conclusions.

        # setup
        self.assertEqual(len(mail.outbox), 0)
        self._twill_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.application_set.count(), 1)

        # email asserts
        orig_email = u.email
        new_email = 'a_different_email@foo.com'
        self.assertNotEqual(orig_email, new_email)

        # visit page
        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/%s/" % a.id))
        tc.code(200)
        self._finish_application_form()
        tc.formvalue('1', 'camp', '1')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.formvalue('1', 'address_email', new_email)
        tc.submit('_save')
        tc.url('officers/applications/$')

        self.assertEqual(u.application_set.count(), 1)

        # Check the e-mails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 1)

        # Read the e-mail
        url, path, querydata = read_email_url(emails[0], 'https?://.*/update-email/.*')

        # Check that nothing has changed yet
        self.assertEqual(User.objects.get(username=OFFICER[0]).email,
                         orig_email)

        # follow link - deliberately wrong first time
        response = self.client.get(path, {'email': new_email, 'hash': 'foo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        self.assertEqual(User.objects.get(username=OFFICER[0]).email,
                         orig_email)

        # follow link, right this time
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update successful")

        # check e-mail address has changed
        self.assertEqual(User.objects.get(username=OFFICER[0]).email, new_email)

        # follow link again -- shouldn't update
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update failed")

        self.assertEqual(User.objects.get(username=OFFICER[0]).email, new_email)

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
        self._finish_application_form()

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
        self.assertEqual(len(self._get_application_form_emails()), 2)

    def test_change_application_after_camp_past(self):
        """
        Ensure that the user can't change an application after it
        has been saved, and the camp is now past.
        """
        self._twill_login(OFFICER)
        a = self._add_application()

        # Make the camp past
        camp = a.camp
        camp.end_date = datetime.date.today() - datetime.timedelta(100)
        camp.save()

        tc.go(make_twill_url("http://www.cciw.co.uk/admin/officers/application/%s/" % a.id))
        tc.code(200)
        tc.formvalue('1', 'full_name', 'A Changed Full Name')
        tc.submit('_save')
        # we should be on same page:
        tc.url('officers/application/%s/$' % a.id)
        # shouldn't have changed data:
        self.assertNotEqual(a.full_name, 'A Changed Full Name')
