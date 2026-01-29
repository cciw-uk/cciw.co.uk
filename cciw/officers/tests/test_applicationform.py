from datetime import date, timedelta

from django.conf import settings
from django.core import mail
from django.core.mail.message import EmailMessage
from django.urls import reverse

from cciw.accounts.models import User
from cciw.cciwmain.tests import factories as camps_factories
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.officers.tests import factories
from cciw.officers.tests.base import RequireQualificationTypesMixin
from cciw.utils.tests.webtest import WebTestBase


class ApplicationFormView(RequireQualificationTypesMixin, WebTestBase):
    def _application_edit_url(self, app_id: int) -> str:
        return reverse("admin:officers_application_change", args=[app_id])

    def _setup(self, *, invitation: bool = True) -> User:
        """
        Initial setup for application form
        """
        # Ensure we have a future camp (need for thisyears_applications logic),
        # but not too far in the future
        user = factories.create_officer()
        leader = factories.create_officer()
        if invitation:
            officers = [user]
        else:
            officers = []
        self.camp = camps_factories.create_camp(
            start_date=date.today() + timedelta(days=20), officers=officers, leader=leader
        )
        self.leader = leader
        self.officer_login(user)
        return user

    def _start_new(self):
        self.get_url("cciw-officers-applications")
        self.submit("input[name=new]")
        self.assertCode(200)

    def _finish_application_form(self, *, enter_dbs_number: bool = False, override: None = None) -> None:
        # A full set of values that pass validation.
        values = {
            "full_name": "x",
            "birth_date": "2000-01-01",
            "birth_place": "x",
            "address_firstline": "x",
            "address_town": "x",
            "address_county": "x",
            "address_postcode": "x",
            "address_country": "x",
            "address_tel": "x",
            "address_mobile": "x",
            "address_email": "foo@foo.com",
            "christian_experience": "x",
            "youth_experience": "x",
            "youth_work_declined_details": "x",
            "illness_details": "x",
            "referee1_name": "My Referee 1",
            "referee1_capacity_known": "Pastor",
            "referee1_address": "x",
            "referee1_tel": "x",
            "referee1_mobile": "x",
            "referee1_email": "foo1@foo1.com",
            "referee2_name": "My Referee 2",
            "referee2_capacity_known": "Boss",
            "referee2_address": "x",
            "referee2_tel": "x",
            "referee2_mobile": "x",
            "referee2_email": "foo2@foo2.com",
            "crime_details": "x",
            "court_details": "x",
            "concern_details": "x",
            "youth_work_declined": "2",
            "relevant_illness": "2",
            "crime_declaration": "2",
            "court_declaration": "2",
            "concern_declaration": "2",
            "allegation_declaration": "2",
            "dbs_check_consent": "2",
            "qualifications-0-type": str(self.first_aid_qualification.id),
            "qualifications-0-issued_on": "2016-01-01",
            "finished": True,
        }
        if enter_dbs_number:
            values["dbs_number"] = "001234"
        if override:
            for k, v in override.items():
                if v is None:
                    del values[k]
                else:
                    values[k] = v
        return self.fill_by_name(values)

    def _get_application_form_emails(self) -> list[EmailMessage]:
        return [e for e in mail.outbox if "Application form" in e.subject]

    def _get_email_change_emails(self) -> list[EmailMessage]:
        return [e for e in mail.outbox if "Email change" in e.subject]

    def _assert_finished_successful(self):
        self.assertNamedUrl("cciw-officers-applications")

        self.assertTextPresent("have been notified of the completed application form by email.")

    def _save(self):
        self.submit("[name=_save]")

    def test_change_application(self):
        user = self._setup()
        app = factories.create_application(finished=False, referee1_name="My Initial Referee 1")
        self.get_literal_url(self._application_edit_url(app.id))
        self.assertCode(200)
        self.assertTextPresent("Save and continue editing")
        # Check that Referee initial values are set from model:
        self.assertTextPresent("My Initial Referee 1")
        self.assertTextAbsent("Save and add another")
        self.fill_by_name({"full_name": "Test full name"})
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        assert user.applications.count() == 1
        app.refresh_from_db()
        assert app.full_name == "Test full name"

        # Check that Referee was propagated properly
        assert app.referee_set.get(referee_number=1).name == "My Initial Referee 1"

    def test_change_finished_application(self):
        """
        Ensure that a leader can change a finished application of an officer
        """
        user = self._setup()
        factories.create_application(officer=user, finished=True)

        self.officer_login(self.leader)
        # To catch a bug, give the leader an application form for the same camp
        factories.create_application(officer=self.leader)

        apps = user.applications.all()
        assert len(apps) == 1
        self.get_literal_url(self._application_edit_url(apps[0].id))
        self.assertCode(200)
        self.fill_by_name({"full_name": "Changed full name"})
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        assert user.applications.count() == 1
        assert user.applications.all()[0].full_name == "Changed full name"

    def _change_email_setup(self) -> tuple[User, str, str, list[EmailMessage]]:
        user = self._setup()
        assert len(mail.outbox) == 0
        application = factories.create_application(finished=False)
        assert user.applications.count() == 1

        # email asserts
        orig_email = user.email
        new_email = "a_different_email@foo.com"
        assert orig_email != new_email

        # visit page
        self.get_literal_url(self._application_edit_url(application.id))
        self.assertCode(200)
        self._finish_application_form()
        self.fill_by_name({"full_name": "Test full name", "address_email": new_email})
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        assert user.applications.count() == 1

        # Check the emails have been sent
        emails = self._get_email_change_emails()
        assert len(emails) == 1
        return user, orig_email, new_email, emails

    def test_change_email_address(self):
        # When submitted email address is different from the one stored against
        # the user, an email should be sent with a link to update the stored
        # email address

        # This is a 'story' test, really, not a unit test, because we want to
        # check several different conclusions.

        user, orig_email, new_email, emails = self._change_email_setup()

        # Read the email
        url, path, querydata = read_email_url(emails[0], "https?://.*/correct-email/.*")

        # Check that nothing has changed yet
        user.refresh_from_db()
        assert user.email == orig_email

        # follow link - deliberately wrong first time
        response = self.client.get(path, {"token": "foo"})
        assert response.status_code == 200
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        user.refresh_from_db()
        assert user.email == orig_email

        # follow link, right this time
        response = self.client.get(path, querydata)
        assert response.status_code == 200
        self.assertContains(response, "Update successful")

        # check email address has changed
        user.refresh_from_db()
        assert user.email == new_email

    def test_change_email_address_mistakenly(self):
        # Same as above, but this time we click the link to correct the
        # application form which has a wrong email address

        user, user_email, application_email, emails = self._change_email_setup()

        # Read the email
        url, path, querydata = read_email_url(emails[0], "https?://.*/correct-application/.*")

        # Check that nothing has changed yet
        assert user.email == user_email
        assert user.applications.all()[0].address_email == application_email

        # follow link - deliberately wrong first time
        response = self.client.get(path, {"token": "foo"})
        assert response.status_code == 200
        self.assertContains(response, "Update failed")

        # Check that nothing has changed yet
        assert user.applications.all()[0].address_email == application_email

        # follow link, right this time
        response = self.client.get(path, querydata)
        assert response.status_code == 200
        self.assertContains(response, "Update successful")

        # check email address has changed
        assert user.applications.all()[0].address_email == user_email

    def test_unchanged_email_address(self):
        """
        Check that if the email address is not changed (or is just different case)
        then no email is sent out
        """
        user = self._setup()
        self._start_new()
        self._finish_application_form()
        self.fill_by_name({"address_email": user.email.upper()})
        self._save()

        # Check no emails have been sent
        emails = self._get_email_change_emails()
        assert len(emails) == 0

    def test_finish_incomplete(self):
        user = self._setup()
        assert user.applications.count() == 0
        self._start_new()
        url = self.current_url
        self.fill_by_name({"finished": True})
        self._save()
        self.assertUrlsEqual(url)  # Same page
        self.assertTextPresent("Please correct the errors below")
        self.assertTextPresent("form-row errors field-address")
        assert user.applications.exclude(saved_on__isnull=True).count() == 0  # shouldn't have been saved

    def test_finish_complete(self):
        user = self._setup()
        assert user.applications.count() == 0
        assert len(mail.outbox) == 0
        self._start_new()

        # Add two applications
        factories.create_application(officer=user, finished=False, saved_on=date(2010, 1, 1))
        # Most recent one:
        application = factories.create_application(officer=user, finished=False)
        self.get_literal_url(self._application_edit_url(application.id))
        self.assertCode(200)
        self._finish_application_form()
        self._save()
        self._assert_finished_successful()

        apps = list(user.applications.all())
        # The old one should have been deleted.
        assert len(apps) == 1
        assert application.id == apps[0].id

        assert apps[0].referee_set.get(referee_number=1).name == "My Referee 1"
        assert apps[0].referee_set.get(referee_number=1).capacity_known == "Pastor"
        assert apps[0].referee_set.get(referee_number=2).name == "My Referee 2"
        assert apps[0].referee_set.get(referee_number=2).capacity_known == "Boss"

        # There should be two emails in outbox, one to officer, one to
        # leader.  This assumes that there is a leader for the camp,
        # and it is associated with a User object.
        emails = self._get_application_form_emails()
        assert len(emails) == 2

        # Email should be sent when application is fully saved.
        for m in emails:
            for txt in ["My Referee 1", "First Aid"]:
                # One to officer should contain attachments, one to leader must
                # not.
                if any(user.email in a for a in m.to):
                    assert txt in m.body
                    assert txt in m.attachments[0][1]
                else:
                    assert txt not in m.body
                    assert len(m.attachments) == 0

    def test_finish_complete_no_invitation(self):
        user = self._setup(invitation=False)
        assert user.applications.count() == 0
        assert len(mail.outbox) == 0
        self._start_new()
        self._finish_application_form()
        self._save()
        self.assertNamedUrl("cciw-officers-applications")
        self.assertTextPresent("The application form has been sent to the CCiW secretary")

        # There should be two emails in outbox, one to officer, one to
        # secretary.
        emails = self._get_application_form_emails()
        assert len(emails) == 2
        assert any(e.to == settings.SECRETARY_EMAILS for e in emails)

    def test_change_application_after_finished(self):
        """
        Ensure that the user can't change an application after it has been
        'finished'
        """
        user = self._setup()
        application = factories.create_application(officer=user, finished=True)

        self.get_literal_url(self._application_edit_url(application.id))
        url = self.current_url
        self.assertCode(200)
        self.fill_by_name({"full_name": "A Changed Full Name"})
        self._save()
        # we should be on same page:
        self.assertUrlsEqual(url)
        self.assertTextPresent("You cannot change a submitted")
        # shouldn't have changed data:
        application.refresh_from_db()
        assert application.full_name != "A Changed Full Name"

    def test_list_applications_officers(self):
        """
        Ensure that normal officers can't see the list of applications
        """
        self.officer_login(factories.create_officer())
        self.get_literal_url(reverse("admin:officers_application_changelist"), expect_errors=[403])
        self.assertCode(403)

    def test_list_applications_leaders(self):
        """
        Ensure that leaders can see the list of applications
        """
        leader = factories.create_current_camp_leader()
        self.officer_login(leader)
        self.get_url("admin:officers_application_changelist")
        self.assertTextPresent("Select application to change")

    def test_add_application_duplicate(self):
        """
        Test that we can't add a new application twice in a year
        """
        user = self._setup()
        factories.create_application(officer=user, saved_on=date.today(), finished=True)
        a2 = factories.create_application(officer=user, saved_on=None, finished=False)
        self.get_literal_url(self._application_edit_url(a2.id))
        self._finish_application_form()
        self._save()
        self.assertTextPresent("You've already submitted")
        assert user.applications.exclude(saved_on__isnull=True).count() == 1

    def test_save_partial(self):
        user = self._setup()
        self._start_new()
        self.fill_by_name({"full_name": "My Name Is ..."})
        self._save()
        apps = user.applications.all()
        assert len(apps) == 1
        a = apps[0]
        assert a.full_name == "My Name Is ..."
        assert not a.finished

    def test_dbs_number_entered(self):
        user = self._setup()
        self._start_new()
        self._finish_application_form(enter_dbs_number=True)
        self._save()
        self._assert_finished_successful()
        a = user.applications.get()
        assert a.dbs_number == "001234"
        assert a.finished
