from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse

from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.officers.applications import application_difference
from cciw.officers.models import Application
from cciw.officers.tests.base import (LEADER, OFFICER, CurrentCampsMixin, OfficersSetupMixin,
                                      RequireQualificationTypesMixin)
from cciw.utils.tests.webtest import WebTestBase

User = get_user_model()


class ApplicationFormView(CurrentCampsMixin, OfficersSetupMixin, RequireQualificationTypesMixin, WebTestBase):

    def _application_edit_url(self, app_id):
        return reverse('admin:officers_application_change', args=[app_id])

    def setUp(self):
        super(ApplicationFormView, self).setUp()

        # Add some invitations:
        u = User.objects.get(username=OFFICER[0])
        for camp in Camp.objects.all():
            u.invitations.create(camp=camp)

    def _add_application(self, officer=OFFICER):
        u = User.objects.get(username=officer[0])
        a = Application(officer=u, address_email=u.email)
        a.save()
        ref, _ = a.referee_set.get_or_create(referee_number=1)
        ref.name = "My Initial Referee 1"
        ref.save()
        return a

    def _finish_application_form(self):
        # A full set of values that pass validation.
        return self.fill_by_name(
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
             'referee1_name': 'My Referee 1',
             'referee1_address': 'x',
             'referee1_tel': 'x',
             'referee1_mobile': 'x',
             'referee1_email': 'foo1@foo1.com',
             'referee2_name': 'My Referee 2',
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
             'qualifications-0-type': str(self.first_aid_qualification.id),
             'qualifications-0-date_issued': '2016-01-01',
             'finished': True,
             })

    def _get_application_form_emails(self):
        return [e for e in mail.outbox if "CCIW application form" in e.subject]

    def _get_email_change_emails(self):
        return [e for e in mail.outbox if "Email change" in e.subject]

    def test_change_application(self):
        self.officer_login(OFFICER)
        a = self._add_application()
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.applications.count(), 1)
        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self.assertTextPresent('Save and continue editing')
        # Check that Referee initial values are set from model:
        self.assertTextPresent('My Initial Referee 1')
        self.assertTextAbsent('Save and add another')
        self.fill_by_name({'full_name': 'Test full name'})
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")
        self.assertEqual(u.applications.count(), 1)
        app = u.applications.all()[0]
        self.assertEqual(app.full_name, 'Test full name')

        # Check that Referee was propagated properly
        self.assertEqual(app.referee_set.get(referee_number=1).name,
                         'My Initial Referee 1')

    def test_change_finished_application(self):
        """
        Ensure that a leader can change a finished application of an officer
        """
        self.test_finish_complete()  # adds app for OFFICER
        self.officer_logout()

        self.officer_login(LEADER)
        # To catch a bug, give the leader an application form for the same camp
        self._add_application(officer=LEADER)
        u = User.objects.get(username=OFFICER[0])
        apps = u.applications.all()
        self.assertEqual(len(apps), 1)
        self.get_literal_url(self._application_edit_url(apps[0].id))
        self.assertCode(200)
        self.fill_by_name({'full_name': 'Changed full name'})
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")
        self.assertEqual(u.applications.count(), 1)
        self.assertEqual(u.applications.all()[0].full_name, 'Changed full name')

    def _change_email_setup(self):
        # setup
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.applications.count(), 1)

        # email asserts
        orig_email = u.email
        new_email = 'a_different_email@foo.com'
        self.assertNotEqual(orig_email, new_email)

        # visit page
        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self._finish_application_form()
        self.fill_by_name({'full_name': 'Test full name',
                           'address_email': new_email})
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")
        self.assertEqual(u.applications.count(), 1)

        # Check the emails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 1)
        return orig_email, new_email, emails

    def test_change_email_address(self):
        # When submitted email address is different from the one stored against
        # the user, an email should be sent with a link to update the stored
        # email address

        # This is a 'story' test, really, not a unit test, because we want to
        # check several different conclusions.

        orig_email, new_email, emails = self._change_email_setup()

        # Read the email
        url, path, querydata = read_email_url(emails[0], 'https?://.*/correct-email/.*')

        # Check that nothing has changed yet
        self.assertEqual(User.objects.get(username=OFFICER[0]).email,
                         orig_email)

        # follow link - deliberately wrong first time
        response = self.client.get(path, {'token': 'foo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        self.assertEqual(User.objects.get(username=OFFICER[0]).email,
                         orig_email)

        # follow link, right this time
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update successful")

        # check email address has changed
        self.assertEqual(User.objects.get(username=OFFICER[0]).email, new_email)

    def test_change_email_address_mistakenly(self):
        # Same as above, but this time we click the link to correct the
        # application form which has a wrong email address

        user_email, application_email, emails = self._change_email_setup()
        user = User.objects.get(username=OFFICER[0])

        # Read the email
        url, path, querydata = read_email_url(emails[0], 'https?://.*/correct-application/.*')

        # Check that nothing has changed yet
        self.assertEqual(user.email, user_email)
        self.assertEqual(user.applications.all()[0].address_email,
                         application_email)

        # follow link - deliberately wrong first time
        response = self.client.get(path, {'token': 'foo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        self.assertEqual(user.applications.all()[0].address_email,
                         application_email)

        # follow link, right this time
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update successful")

        # check email address has changed
        self.assertEqual(user.applications.all()[0].address_email,
                         user_email)

    def test_unchanged_email_address(self):
        """
        Check that if the email address is not changed (or is just different case)
        then no email is sent out
        """
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        a = self._add_application()
        self.assertEqual(u.applications.count(), 1)

        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self._finish_application_form()
        self.fill_by_name({'address_email': u.email.upper()})
        self.submit('[name=_save]')

        # Check no emails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 0)

    def test_finish_incomplete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.applications.count(), 0)
        self.officer_login(OFFICER)
        a = self._add_application()
        self.get_literal_url(self._application_edit_url(a.id))
        url = self.current_url
        self.assertCode(200)
        self.fill_by_name({'finished': True})
        self.submit('[name=_save]')
        self.assertUrlsEqual(url)  # Same page
        self.assertTextPresent("Please correct the errors below")
        self.assertTextPresent("form-row errors field-address")
        self.assertEqual(u.applications.exclude(date_submitted__isnull=True).count(), 0)  # shouldn't have been saved

    def test_finish_complete(self):
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.applications.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        # An old, unfinished application form
        self._add_application()
        a = self._add_application()
        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self._finish_application_form()
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")

        self.assertTextPresent("The completed application form has been sent to the leaders (Dave & Rebecca Stott) via email")

        apps = list(u.applications.all())
        # The old one should have been deleted.
        self.assertEqual(len(apps), 1)
        self.assertEqual(a.id, apps[0].id)

        self.assertEqual(apps[0].referee_set.get(referee_number=1).name,
                         'My Referee 1')
        self.assertEqual(apps[0].referee_set.get(referee_number=2).name,
                         'My Referee 2')

        # There should be two emails in outbox, one to officer, one to
        # leader.  This assumes that there is a leader for the camp,
        # and it is associated with a User object.
        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)

        # Email should be sent when application is fully saved.
        for m in emails:
            for txt in ['My Referee 1', 'First Aid']:
                self.assertIn(txt, m.body)
                self.assertIn(txt, m.attachments[0][1])

    def test_finish_complete_no_officer_list(self):
        u = User.objects.get(username=OFFICER[0])
        u.invitations.all().delete()
        self.assertEqual(u.applications.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        a = self._add_application()
        self.get_literal_url(self._application_edit_url(a.id))
        self._finish_application_form()
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")
        self.assertTextPresent("The application form has been sent to the CCIW secretary")

        # There should be two emails in outbox, one to officer, one to
        # secretary.
        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)
        self.assertTrue(any(e.to == [settings.SECRETARY_EMAIL] for e in emails))

    def test_change_application_after_camp_past(self):
        """
        Ensure that the user can't change an application after it has been
        'finished'
        """
        self.officer_login(OFFICER)
        a = self._add_application()
        a.finished = True
        a.save()

        self.get_literal_url(self._application_edit_url(a.id))
        url = self.current_url
        self.assertCode(200)
        self.fill_by_name({'full_name': 'A Changed Full Name'})
        self.submit('[name=_save]')
        # we should be on same page:
        self.assertUrlsEqual(url)
        self.assertTextPresent("You cannot change a submitted")
        # shouldn't have changed data:
        self.assertNotEqual(a.full_name, 'A Changed Full Name')

    def test_list_applications_officers(self):
        """
        Ensure that normal officers can't see the list of applications
        """
        self.officer_login(OFFICER)
        self.get_literal_url(reverse("admin:officers_application_changelist"),
                             expect_errors=[403])
        self.assertCode(403)

    def test_list_applications_leaders(self):
        """
        Ensure that leaders can see the list of applications
        """
        self.officer_login(LEADER)
        self.get_url("admin:officers_application_changelist")
        self.assertTextPresent("Select application to change")

    def test_add_application_duplicate(self):
        """
        Test that we can't add a new application twice in a year
        """
        self.officer_login(OFFICER)
        a1 = self._add_application()
        a1.date_submitted = date.today()
        a1.save()
        a2 = self._add_application()
        self.get_literal_url(self._application_edit_url(a2.id))
        self._finish_application_form()
        self.submit('[name=_save]')
        self.assertTextPresent("You've already submitted")
        u = User.objects.get(username=OFFICER[0])
        self.assertEqual(u.applications.exclude(date_submitted__isnull=True).count(), 1)

    def test_application_differences_email(self):
        """
        Tests the 'application difference' email that is sent when an
        application form is submitted
        """
        u = User.objects.get(username=OFFICER[0])

        # Create one application
        self.test_finish_complete()

        # Empty outbox
        mail.outbox[:] = []

        # Change the date on the existing app, so that we can
        # create a new one
        app0 = u.applications.all()[0]
        app0.date_submitted = date.today() + timedelta(-365)
        app0.save()

        # Create another application
        app1 = self._add_application()
        self.get_literal_url(self._application_edit_url(app1.id))
        self._finish_application_form()
        # Now change some values
        self.fill_by_name({'full_name': 'New Full Name'})
        self.submit('[name=_save]')
        self.assertNamedUrl("cciw-officers-applications")

        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)
        leader_email = [e for e in emails
                        if e.subject == 'CCIW application form from New Full Name'][0]
        msg = leader_email.message()

        # Email will have 3 parts - text, RTF, and differences from last year
        # as an HTML file.
        attachments = msg.get_payload()
        self.assertEqual(len(attachments), 3)

        # Testing the actual content is hard from this point, due to email
        # formatting, so we do it manually:

        apps = u.applications.order_by('date_submitted')
        assert len(apps) == 2

        application_diff = application_difference(apps[0], apps[1])
        self.assertTrue('>new full name</ins>'
                        in application_diff.lower())
        self.assertTrue('>x</del>'
                        in application_diff.lower())
