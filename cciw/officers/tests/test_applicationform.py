import datetime

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application
from cciw.officers.applications import application_difference
from cciw.officers.tests.references import OFFICER, LEADER
from cciw.utils.tests.webtest import WebTestBase

class ApplicationFormView(WebTestBase):
    fixtures = ['basic.json', 'officers_users.json']

    def _application_edit_url(self, app_id):
        return reverse('admin:officers_application_change', args=[app_id])

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

    def _finish_application_form(self, response):
        # A full set of values that pass validation.
        return self.fill(response.forms['application_form'],
                         {'full_name': 'x',
                          'full_maiden_name': 'x',
                          'birth_date': '2000-01-01',
                          'birth_place': 'x',
                          'address_firstline': 'x',
                          'address_town': 'x',
                          'address_county': 'x',
                          'address_postcode': 'x',
                          'address_country': 'x',
                          'address_tel': 'x',
                          'address_mobile': 'x',
                          'address_since': '2008/01',
                          'address_email': 'foo@foo.com',
                          'christian_experience': 'x',
                          'youth_experience': 'x',
                          'youth_work_declined_details': 'x',
                          'illness_details': 'x',
                          'employer1_name': 'x',
                          'employer1_from': '2008/01',
                          'employer1_to': '2008/01',
                          'employer1_job': 'x',
                          'employer1_leaving': 'x',
                          'employer2_name': 'x',
                          'employer2_from': '2008/01',
                          'employer2_to': '2008/01',
                          'employer2_job': 'x',
                          'employer2_leaving': 'x',
                          'referee1_name': 'x',
                          'referee1_address': 'x',
                          'referee1_tel': 'x',
                          'referee1_mobile': 'x',
                          'referee1_email': 'foo1@foo1.com',
                          'referee2_name': 'x',
                          'referee2_address': 'x',
                          'referee2_tel': 'x',
                          'referee2_mobile': 'x',
                          'referee2_email': 'foo2@foo2.com',
                          'crime_details': 'x',
                          'court_details': 'x',
                          'concern_details': 'x',
                          'youth_work_declined': '2',
                          'relevant_illness': '2',
                          'crime_declaration': '2',
                          'court_declaration': '2',
                          'concern_declaration': '2',
                          'allegation_declaration': '2',
                          'crb_check_consent': '2',
                          'finished': 'on',
                          })

    def _get_application_form_emails(self):
        return [e for e in mail.outbox if "CCIW application form" in e.subject]

    def _get_email_change_emails(self):
        return [e for e in mail.outbox if "E-mail change" in e.subject]

    def test_change_application(self):
        self.webtest_officer_login(OFFICER)
        a = self._add_application()
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 1)
        response = self.get(self._application_edit_url(a.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save and continue editing')
        self.assertNotContains(response, 'Save and add another')
        response = self.fill(response.forms['application_form'], {'full_name': 'Test full name'}).submit('_save').follow()
        self.assertUrl(response, "cciw.officers.views.applications")
        self.assertEqual(u.application_set.count(), 1)
        self.assertEqual(u.application_set.all()[0].full_name, 'Test full name')

    def test_change_finished_application(self):
        """
        Ensure that a leader can change a finished application of an officer
        """
        self.test_finish_complete() # adds app for OFFICER
        self.webtest_officer_logout()

        self.webtest_officer_login(LEADER)
        # To catch a bug, give the leader an application form for the same camp
        self._add_application(officer=LEADER)
        u = User.objects.get(username=OFFICER[0])
        apps = u.application_set.all()
        self.assertEqual(len(apps), 1)
        response = self.get(self._application_edit_url(apps[0].id))
        self.assertEqual(response.status_code, 200)
        response = self.fill(response.forms['application_form'],
                             {'full_name': 'Changed full name'}).submit('_save').follow()
        self.assertUrl(response, "cciw.officers.views.applications")
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
        self.webtest_officer_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.application_set.count(), 1)

        # email asserts
        orig_email = u.email
        new_email = 'a_different_email@foo.com'
        self.assertNotEqual(orig_email, new_email)

        # visit page
        response = self.get(self._application_edit_url(a.id))
        self.assertEqual(response.status_code, 200)
        self._finish_application_form(response)
        response = self.fill(response.forms['application_form'],
                             {'full_name': 'Test full name',
                              'address_email': new_email}).submit('_save').follow()
        self.assertUrl(response, "cciw.officers.views.applications")
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
        self.webtest_officer_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.application_set.count(), 1)

        response = self.get(self._application_edit_url(a.id))
        self.assertEqual(response.status_code, 200)
        self._finish_application_form(response)
        response = self.fill(response.forms['application_form'],
                             {'address_email': u.email.upper()}).submit('_save').follow()

        # Check no e-mails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 0)

    def test_finish_incomplete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self.webtest_officer_login(OFFICER)
        a = self._add_application()
        response = self.get(self._application_edit_url(a.id))
        url = response.request.url
        self.assertEqual(response.status_code, 200)
        response = self.fill(response.forms['application_form'], {'finished': 'on'}).submit('_save')
        self.assertEqual(url, response.request.url) # Same page
        self.assertContains(response, "Please correct the errors below")
        self.assertContains(response, "form-row errors field-address")
        self.assertEqual(u.application_set.exclude(date_submitted__isnull=True).count(), 0) # shouldn't have been saved

    def test_finish_complete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.application_set.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.webtest_officer_login(OFFICER)
        # An old, unfinished application form
        self._add_application()
        a = self._add_application()
        response = self.get(self._application_edit_url(a.id))
        self.assertEqual(response.status_code, 200)
        response = self._finish_application_form(response).submit('_save').follow()
        self.assertUrl(response, "cciw.officers.views.applications")

        self.assertContains(response, "The completed application form has been sent to the leaders (Dave &amp; Rebecca Stott) via e-mail")

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
        self.webtest_officer_login(OFFICER)
        a = self._add_application()
        a.finished = True
        a.save()

        response = self.get(self._application_edit_url(a.id))
        url = response.request.url
        self.assertEqual(response.status_code, 200)
        response = self.fill(response.forms['application_form'],
                             {'full_name': 'A Changed Full Name'}).submit('_save')
        # we should be on same page:
        self.assertEqual(url, response.request.url)
        self.assertContains(response, "You cannot change a submitted")
        # shouldn't have changed data:
        self.assertNotEqual(a.full_name, 'A Changed Full Name')

    def test_list_applications_officers(self):
        """
        Ensure that normal officers can't see the list of applications
        """
        self.webtest_officer_login(OFFICER)
        response = self.app.get(reverse("admin:officers_application_changelist"),
                                expect_errors=[403])
        self.assertEqual(response.status_code, 403)

    def test_list_applications_leaders(self):
        """
        Ensure that leaders can see the list of applications
        """
        self.webtest_officer_login(LEADER)
        response = self.get("admin:officers_application_changelist")
        self.assertEqual(response.status_code, 200)

    def test_add_application_duplicate(self):
        """
        Test that we can't add a new application twice in a year
        """
        self.webtest_officer_login(OFFICER)
        a1 = self._add_application()
        a1.date_submitted = datetime.date.today()
        a1.save()
        a2 = self._add_application()
        response = self.get(self._application_edit_url(a2.id))
        response = self._finish_application_form(response).submit('_save')
        self.assertContains(response, "You&#39;ve already submitted")
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
        response = self.get(self._application_edit_url(app1.id))
        self._finish_application_form(response)
        # Now change some values
        response = self.fill(response.forms['application_form'],
                             {'full_name': 'New Full Name'}).submit('_save').follow()
        self.assertUrl(response, "cciw.officers.views.applications")

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
        self.assertTrue('>new full name</ins>'
                        in application_diff.lower())
        self.assertTrue('>x</del>'
                        in application_diff.lower())
