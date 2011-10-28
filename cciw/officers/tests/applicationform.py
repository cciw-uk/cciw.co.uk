import datetime

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from twill import commands as tc

from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.applications import application_difference
from cciw.officers.tests.references import OFFICER, LEADER
from cciw.utils.tests.twillhelpers import TwillMixin, make_django_url

class ApplicationFormView(TwillMixin, TestCase):
    fixtures = ['basic.json', 'officers_users.json']

    def _application_edit_url(self, app_id):
        return make_django_url('admin:officers_application_change', app_id)

    def setUp(self):
        # Make sure second camp has end date in future, otherwise we won't be able to
        # save. Previous camp should be one year earlier
        Camp.objects.filter(id=1).update(start_date=datetime.date.today() + datetime.timedelta(100-365),
                                         end_date=datetime.date.today() + datetime.timedelta(107-365))
        Camp.objects.filter(id=2).update(start_date=datetime.date.today() + datetime.timedelta(100),
                                         end_date=datetime.date.today() + datetime.timedelta(107))

        # Add some invitations:
        u = User.objects.get(username=OFFICER[0])
        for pk in [1,2]:
            u.invitation_set.create(camp=Camp.objects.get(id=pk))

        super(ApplicationFormView, self).setUp()

    def _add_application(self, officer=OFFICER):
        u = User.objects.get(username=officer[0])
        a = Application(officer=u, address_email=u.email)
        a.save()
        return a

    def _finish_application_form(self):
        # A full set of values that pass validation.
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
        return [e for e in mail.outbox if "E-mail change" in e.subject]

    def test_change_application(self):
        self._twill_login(OFFICER)
        a = self._add_application()
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 1)
        tc.go(self._application_edit_url(a.id))
        tc.code(200)
        tc.find('Save and continue editing')
        tc.notfind('Save and add another')
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.submit('_save')
        tc.url(reverse("cciw.officers.views.applications"))
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')

    def test_change_finished_application(self):
        """
        Ensure that a leader can change a finished application of an officer
        """
        self.test_finish_complete() # adds app for OFFICER
        self._twill_logout()

        self._twill_login(LEADER)
        # To catch a bug, give the leader an application form for the same camp
        self._add_application(officer=LEADER)
        u = User.objects.get(username=OFFICER[0])
        apps = u.application_set.all()
        self.assertEqual(len(apps), 1)
        tc.go(self._application_edit_url(apps[0].id))
        tc.code(200)
        tc.formvalue('1', 'full_name', 'Changed full name')
        tc.submit('_save')
        tc.url(reverse("cciw.officers.views.applications"))
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Changed full name')

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
        tc.go(self._application_edit_url(a.id))
        tc.code(200)
        self._finish_application_form()
        tc.formvalue('1', 'full_name', 'Test full name')
        tc.formvalue('1', 'address_email', new_email)
        tc.submit('_save')
        tc.url(reverse("cciw.officers.views.applications"))

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

    def test_unchanged_email_address(self):
        """
        Check that if the e-mail address is not changed (or is just different case)
        then no e-mail is sent out
        """
        self.assertEqual(len(mail.outbox), 0)
        self._twill_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.application_set.count(), 1)

        tc.go(self._application_edit_url(a.id))
        tc.code(200)
        self._finish_application_form()
        tc.formvalue('1', 'address_email', u.email.upper())
        tc.submit('_save')

        # Check no e-mails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 0)

    def test_finish_incomplete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self._twill_login(OFFICER)
        a = self._add_application()
        tc.go(self._application_edit_url(a.id))
        url = tc.browser.get_url()
        tc.code(200)
        tc.formvalue('1', 'finished', 'on')
        tc.submit('_save')
        tc.url(url)
        tc.find("Please correct the errors below")
        tc.find("form-row errors field-address")
        self.assertEqual(u.application_set.exclude(date_submitted__isnull=True).count(), 0) # shouldn't have been saved

    def test_finish_complete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self._twill_login(OFFICER)
        # An old, unfinished application form
        self._add_application()
        a = self._add_application()
        tc.go(self._application_edit_url(a.id))
        tc.code(200)
        self._finish_application_form()

        tc.submit('_save')
        tc.url(reverse("cciw.officers.views.applications"))

        apps = list(u.application_set.all())
        # The old one should have been deleted.
        self.assertEqual(len(apps), 1)
        self.assertEqual(a.id, apps[0].id)

        # There should be two emails in outbox, one to officer, one to
        # leader.  This assumes that there is a leader for the camp,
        # and it is associated with a User object.
        self.assertEqual(len(self._get_application_form_emails()), 2)

    def test_change_application_after_camp_past(self):
        """
        Ensure that the user can't change an application after it has been
        'finished'
        """
        self._twill_login(OFFICER)
        a = self._add_application()
        a.finished = True
        a.save()

        tc.go(self._application_edit_url(a.id))
        url = tc.browser.get_url()
        tc.code(200)
        tc.formvalue('1', 'full_name', 'A Changed Full Name')
        tc.submit('_save')
        # we should be on same page:
        tc.url(url)
        tc.find("You cannot change a submitted")
        # shouldn't have changed data:
        self.assertNotEqual(a.full_name, 'A Changed Full Name')

    def test_list_applications_officers(self):
        """
        Ensure that normal officers can't see the list of applications
        """
        self._twill_login(OFFICER)
        tc.go(make_django_url("admin:officers_application_changelist"))
        tc.code(403)

    def test_list_applications_leaders(self):
        """
        Ensure that leaders can see the list of applications
        """
        self._twill_login(LEADER)
        tc.go(make_django_url("admin:officers_application_changelist"))
        tc.code(200)

    def test_add_application_duplicate(self):
        """
        Test that we can't add a new application twice in a year
        """
        self._twill_login(OFFICER)
        a1 = self._add_application()
        a1.date_submitted = datetime.date.today()
        a1.save()
        a2 = self._add_application()
        tc.go(self._application_edit_url(a2.id))
        self._finish_application_form()
        tc.submit('_save')
        tc.find("You&#39;ve already submitted")
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.exclude(date_submitted__isnull=True).count(), 1)

    def test_application_differences_email(self):
        """
        Tests the 'application difference' e-mail that is sent when an
        application form is submitted
        """
        u = User.objects.get(username=OFFICER[0])

        # Create one application
        self.test_finish_complete()

        # Empty outbox
        mail.outbox[:] = []

        # Change the date on the existing app, so that we can
        # create a new one
        app0 = u.application_set.all()[0]
        app0.date_submitted = datetime.date.today() + datetime.timedelta(-365)
        app0.save()

        # Create another application
        app1 = self._add_application()
        tc.go(self._application_edit_url(app1.id))
        self._finish_application_form()
        # Now change some values
        tc.formvalue('1', 'full_name', 'New Full Name')
        tc.submit('_save')
        tc.url(reverse("cciw.officers.views.applications"))

        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)
        leader_email = [e for e in emails
                        if e.subject == u'CCIW application form from New Full Name'][0]
        msg = leader_email.message()

        # E-mail will have 3 parts - text, RTF, and differences from last year
        # as an HTML file.
        attachments = msg.get_payload()
        self.assertEqual(len(attachments), 3)

        # Testing the actual content is hard from this point, due to e-mail
        # formatting, so we do it manually:

        apps = u.application_set.order_by('date_submitted')
        assert len(apps) == 2

        application_diff = application_difference(apps[0], apps[1])
        self.assertTrue('>New Full Name</INS>'
                        in application_diff)
        self.assertTrue('>x</DEL>'
                        in application_diff)
