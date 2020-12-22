# -*- coding: utf-8 -*-
from datetime import date

from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.officers.models import Application
from cciw.officers.tests.base import (LEADER, OFFICER, OFFICER_EMAIL, CurrentCampsMixin, OfficersSetupMixin,
                                      RequireQualificationTypesMixin)
from cciw.utils.tests.webtest import WebTestBase


class ApplicationFormView(CurrentCampsMixin, OfficersSetupMixin, RequireQualificationTypesMixin, WebTestBase):

    def _application_edit_url(self, app_id):
        return reverse('admin:officers_application_change', args=[app_id])

    def setUp(self):
        super().setUp()

        # Add some invitations:
        u = self._get_user(OFFICER)
        for camp in Camp.objects.all():
            u.invitations.create(camp=camp)

    def _get_user(self, user_details):
        return User.objects.get(username=user_details[0])

    def _add_application(self, officer=OFFICER):
        u = self._get_user(officer)
        a = Application(officer=u, address_email=u.email)
        a.save()
        ref, _ = a.referee_set.get_or_create(referee_number=1)
        ref.name = "My Initial Referee 1"
        ref.save()
        return a

    def _start_new(self):
        self.get_url('cciw-officers-applications')
        self.submit('input[name=new]')
        self.assertCode(200)

    def _finish_application_form(self, enter_dbs_number=False, override=None):
        # A full set of values that pass validation.
        values = \
            {'full_name': 'x',
             'birth_date': '2000-01-01',
             'birth_place': 'x',
             'address_firstline': 'x',
             'address_town': 'x',
             'address_county': 'x',
             'address_postcode': 'x',
             'address_country': 'x',
             'address_tel': 'x',
             'address_mobile': 'x',
             'address_email': 'foo@foo.com',
             'christian_experience': 'x',
             'youth_experience': 'x',
             'youth_work_declined_details': 'x',
             'illness_details': 'x',
             'referee1_name': 'My Referee 1',
             'referee1_capacity_known': 'Pastor',
             'referee1_address': 'x',
             'referee1_tel': 'x',
             'referee1_mobile': 'x',
             'referee1_email': 'foo1@foo1.com',
             'referee2_name': 'My Referee 2',
             'referee2_capacity_known': 'Boss',
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
             'dbs_check_consent': '2',
             'qualifications-0-type': str(self.first_aid_qualification.id),
             'qualifications-0-date_issued': '2016-01-01',
             'finished': True,
             }
        if enter_dbs_number:
            values['dbs_number'] = '001234'
        if override:
            for k, v in override.items():
                if v is None:
                    del values[k]
                else:
                    values[k] = v
        return self.fill_by_name(values)

    def _get_application_form_emails(self):
        return [e for e in mail.outbox if "Application form" in e.subject]

    def _get_email_change_emails(self):
        return [e for e in mail.outbox if "Email change" in e.subject]

    def _assert_finished_successful(self):
        self.assertNamedUrl("cciw-officers-applications")

        self.assertTextPresent("The leaders (Dave & Rebecca Stott) have been notified of the completed application form by email.")

    def _save(self):
        self.submit('[name=_save]')

    def test_change_application(self):
        self.officer_login(OFFICER)
        # An unfinished application form:
        a = self._add_application()
        u = self._get_user(OFFICER)
        self.assertEqual(u.applications.count(), 1)
        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self.assertTextPresent('Save and continue editing')
        # Check that Referee initial values are set from model:
        self.assertTextPresent('My Initial Referee 1')
        self.assertTextAbsent('Save and add another')
        self.fill_by_name({'full_name': 'Test full name'})
        self._save()
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
        u = self._get_user(OFFICER)
        apps = u.applications.all()
        self.assertEqual(len(apps), 1)
        self.get_literal_url(self._application_edit_url(apps[0].id))
        self.assertCode(200)
        self.fill_by_name({'full_name': 'Changed full name'})
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        self.assertEqual(u.applications.count(), 1)
        self.assertEqual(u.applications.all()[0].full_name, 'Changed full name')

    def _change_email_setup(self):
        # setup
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        u = self._get_user(OFFICER)
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
        self._save()
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
        self.assertEqual(self._get_user(OFFICER).email,
                         orig_email)

        # follow link - deliberately wrong first time
        response = self.client.get(path, {'token': 'foo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        self.assertEqual(self._get_user(OFFICER).email,
                         orig_email)

        # follow link, right this time
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update successful")

        # check email address has changed
        self.assertEqual(self._get_user(OFFICER).email, new_email)

    def test_change_email_address_mistakenly(self):
        # Same as above, but this time we click the link to correct the
        # application form which has a wrong email address

        user_email, application_email, emails = self._change_email_setup()
        user = self._get_user(OFFICER)

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
        u = self._get_user(OFFICER)
        self._start_new()
        self._finish_application_form()
        self.fill_by_name({'address_email': u.email.upper()})
        self._save()

        # Check no emails have been sent
        emails = self._get_email_change_emails()
        self.assertEqual(len(emails), 0)

    def test_finish_incomplete(self):
        u = self._get_user(OFFICER)
        self.assertEqual(u.applications.count(), 0)
        self.officer_login(OFFICER)
        self._start_new()
        url = self.current_url
        self.fill_by_name({'finished': True})
        self._save()
        self.assertUrlsEqual(url)  # Same page
        self.assertTextPresent("Please correct the errors below")
        self.assertTextPresent("form-row errors field-address")
        self.assertEqual(u.applications.exclude(date_saved__isnull=True).count(), 0)  # shouldn't have been saved

    def test_finish_complete(self):
        u = self._get_user(OFFICER)
        self.assertEqual(u.applications.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        self._start_new()

        # Add two applications
        self._add_application()  # old, unfinshed one
        a = self._add_application()  # most recent
        self.get_literal_url(self._application_edit_url(a.id))
        self.assertCode(200)
        self._finish_application_form()
        self._save()
        self._assert_finished_successful()

        apps = list(u.applications.all())
        # The old one should have been deleted.
        self.assertEqual(len(apps), 1)
        self.assertEqual(a.id, apps[0].id)

        self.assertEqual(apps[0].referee_set.get(referee_number=1).name,
                         'My Referee 1')
        self.assertEqual(apps[0].referee_set.get(referee_number=1).capacity_known,
                         'Pastor')
        self.assertEqual(apps[0].referee_set.get(referee_number=2).name,
                         'My Referee 2')
        self.assertEqual(apps[0].referee_set.get(referee_number=2).capacity_known,
                         'Boss')

        # There should be two emails in outbox, one to officer, one to
        # leader.  This assumes that there is a leader for the camp,
        # and it is associated with a User object.
        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)

        # Email should be sent when application is fully saved.
        for m in emails:
            for txt in ['My Referee 1', 'First Aid']:
                # One to officer should contain attachments, one to leader must
                # not.
                if any(OFFICER_EMAIL in a for a in m.to):
                    self.assertIn(txt, m.body)
                    self.assertIn(txt, m.attachments[0][1])
                else:
                    self.assertNotIn(txt, m.body)
                    self.assertEqual(len(m.attachments), 0)

    def test_finish_complete_no_officer_list(self):
        u = self._get_user(OFFICER)
        u.invitations.all().delete()
        self.assertEqual(u.applications.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.officer_login(OFFICER)
        self._start_new()
        self._finish_application_form()
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        self.assertTextPresent("The application form has been sent to the CCiW secretary")

        # There should be two emails in outbox, one to officer, one to
        # secretary.
        emails = self._get_application_form_emails()
        self.assertEqual(len(emails), 2)
        self.assertTrue(
            any(e.to == settings.SECRETARY_EMAILS for e in emails))

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
        self._save()
        # we should be on same page:
        self.assertUrlsEqual(url)
        self.assertTextPresent("You cannot change a submitted")
        # shouldn't have changed data:
        a = Application.objects.get(id=a.id)
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
        a1.date_saved = date.today()
        a1.save()
        a2 = self._add_application()
        self.get_literal_url(self._application_edit_url(a2.id))
        self._finish_application_form()
        self._save()
        self.assertTextPresent("You've already submitted")
        u = self._get_user(OFFICER)
        self.assertEqual(u.applications.exclude(date_saved__isnull=True).count(), 1)

    def test_save_partial(self):
        self.officer_login(OFFICER)
        self._start_new()
        self.fill_by_name({'full_name': 'My Name Is ...'})
        self._save()
        user = self._get_user(OFFICER)
        apps = user.applications.all()
        self.assertEqual(len(apps), 1)
        a = apps[0]
        self.assertEqual(a.full_name, 'My Name Is ...')
        self.assertEqual(a.finished, False)

    def test_dbs_number_entered(self):
        self.officer_login(OFFICER)
        self._start_new()
        self._finish_application_form(enter_dbs_number=True)
        self._save()
        self._assert_finished_successful()
        a = self._get_user(OFFICER).applications.get()
        self.assertEqual(a.dbs_number, '001234')
        self.assertEqual(a.finished, True)
