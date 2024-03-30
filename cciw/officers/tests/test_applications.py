from datetime import date, timedelta

from django.core import mail

from cciw.accounts.models import User
from cciw.cciwmain.tests import factories as camps_factories
from cciw.officers import applications
from cciw.officers.models import Application, Qualification
from cciw.officers.tests import factories
from cciw.officers.tests.base import RequireQualificationTypesMixin
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import WebTestBase


class ApplicationModel(TestBase):
    def test_referees(self):
        app1 = factories.create_application()
        app2 = factories.create_application()
        app3 = factories.create_application()

        assert app1.referee_set.count() == 2
        app3.referee_set.all().delete()
        assert app3.referee_set.count() == 0

        # Test that 'referees' property works with and without prefetch,
        # and with no referees existing
        app1 = Application.objects.prefetch_related("referee_set").get(id=app1.id)
        app2 = Application.objects.get(id=app2.id)
        app3 = Application.objects.get(id=app3.id)

        for app in [app1, app2, app3]:
            assert app.referees[0] == app.referee_set.get(referee_number=1)
            assert app.referees[1] == app.referee_set.get(referee_number=2)


class PersonalApplicationList(RequireQualificationTypesMixin, WebTestBase):
    _create_button = """<input type="submit" name="new" value="Create" """
    _edit_button = """<input type="submit" name="edit" value="Continue" """

    def _start(self, old=False, finished=False, unfinished=False, qualifications=None):
        """
        Create camp and officer, optionally with:
        - a recent *finished* Application
        - an *old* finished* Application
        - a recent *unfinished* Application
        - any specificed Qualifications in Applications

        And go to Applications list page
        """
        officer = factories.create_officer()
        # Ensure we have a future camp, but not too far in the future
        camps_factories.create_camp(start_date=date.today() + timedelta(days=20))
        if old:
            factories.create_application(
                officer=officer,
                finished=True,
                saved_on=date.today() - timedelta(days=365),
                qualifications=qualifications,
            )
        if finished:
            factories.create_application(
                officer=officer,
                finished=True,
                saved_on=date.today() - timedelta(days=1),
                qualifications=qualifications,
            )
        if unfinished:
            factories.create_application(
                officer=officer,
                finished=False,
                saved_on=date.today() - timedelta(days=1),
                qualifications=qualifications,
            )
        self.officer_login(officer)
        self.get_url("cciw-officers-applications")
        return officer

    def test_no_existing_application(self):
        self._start(finished=False, unfinished=False, old=False)
        self.assertTextPresent("Your applications")
        assert self.is_element_present("input[type=submit][value=Start]")
        assert not self.is_element_present("input[type=submit][value=Create]")
        assert not self.is_element_present("input[type=submit][name=edit]")

    def test_finished_application_old(self):
        self._start(old=True)
        assert not self.is_element_present("input[type=submit][value=Start]")
        assert self.is_element_present("input[type=submit][value=Create]")
        assert not self.is_element_present("input[type=submit][name=edit]")

    def test_finished_application_recent(self):
        self._start(finished=True)
        assert not self.is_element_present("input[type=submit][value=Start]")
        assert not self.is_element_present("input[type=submit][value=Create]")
        assert not self.is_element_present("input[type=submit][name=edit]")

    def test_unfinished_application(self):
        self._start(unfinished=True)
        assert self.is_element_present("input[type=submit][name=edit]")

    def test_create_from_old(self):
        officer = self._start(
            old=True,
            qualifications=[Qualification(type=self.first_aid_qualification, issued_on=date(2016, 1, 1))],
        )
        application = officer.applications.get()

        self.submit("input[type=submit][value=Create]")
        assert len(officer.applications.all()) == 2
        # New should be a copy of old:
        for a in officer.applications.all():
            assert a.full_name == application.full_name
            assert a.referee_set.get(referee_number=1).name == application.referee_set.get(referee_number=1).name
            assert list([q.type, q.issued_on] for q in a.qualifications.all()) == list(
                [q.type, q.issued_on] for q in application.qualifications.all()
            )

    def test_create_when_already_done(self):
        officer = self._start(old=True)

        # Page is already loaded, at this point we submit an application (e.g. in different tab)
        factories.create_application(officer=officer, finished=True, saved_on=date.today() - timedelta(days=1))
        assert officer.applications.count() == 2

        # And then try to create.
        # It should not create a new application since recent one is submitted
        self.submit("input[type=submit][value=Create]")
        assert officer.applications.count() == 2


class PersonalApplicationView(WebTestBase):
    def submit(self):
        super().submit('input[value="Get it"]')

    def test_view_txt_rtf_html(self):
        officer = self.officer_login()
        application = factories.create_application(
            officer=officer,
            full_name="Joe Winston Bloggs",
        )

        self.get_url("cciw-officers-applications")
        self.fill({"#application": application.id, "#format": "txt"})
        self.submit()
        assert self.last_response.content_type == "text/plain"
        assert b"Joe Winston Bloggs" in self.last_response.content

        self.get_url("cciw-officers-applications")
        self.fill({"#application": application.id, "#format": "rtf"})
        self.submit()
        assert self.last_response.content_type == "text/rtf"
        assert b"\\cell Joe Winston Bloggs" in self.last_response.content

        self.get_url("cciw-officers-applications")
        self.fill({"#application": application.id, "#format": "html"})
        self.submit()
        self.assertTextPresent("Joe Winston Bloggs")

    def test_view_email(self):
        officer = self.officer_login()
        application = factories.create_application(
            officer=officer,
            full_name="Joe Winston Bloggs",
        )
        self.get_url("cciw-officers-applications")
        self.fill({"#application": application.id, "#format": "send"})
        self.submit()
        self.assertTextPresent("Email sent")

        m = mail.outbox[0]
        assert "Joe Winston Bloggs" in m.body
        fname, fdata, ftype = m.attachments[0]
        app_date = application.saved_on

        assert fname == f"Application_{officer.username}_{app_date.year:04}-{app_date.month:02}-{app_date.day:02}.rtf"
        assert "\\cell Joe Winston Bloggs" in fdata
        assert ftype == "text/rtf"


class ApplicationUtils(TestBase):
    def test_saved_on_logic(self):
        # Setup::
        # * two camps, different years, but within 12 months of each
        #   other.
        # * An application form that is submitted just before the first.
        #   This should not appear in the following years applications.
        # * An application form for the second year, that is submitted
        #   just after the last camp for the first year

        # We have to use datetime.today(), because this is used by
        # thisyears_applications.

        future_camp_start = date(date.today().year + 1, 8, 1)
        past_camp_start = future_camp_start - timedelta(30 * 11)

        c1 = camps_factories.create_camp(
            year=past_camp_start.year,
            start_date=past_camp_start,
        )
        c2 = camps_factories.create_camp(
            year=future_camp_start.year,
            start_date=future_camp_start,
        )
        u = User.objects.create(username="test")
        u.invitations.create(camp=c1)
        u.invitations.create(camp=c2)

        app1 = Application.objects.create(officer=u, finished=True, saved_on=past_camp_start - timedelta(1))

        # First, check we don't have any apps that are counted as 'this years'
        assert not applications.thisyears_applications(u).exists()

        # Create an application for this year
        app2 = Application.objects.create(officer=u, finished=True, saved_on=past_camp_start + timedelta(10))

        # Now we should have one
        assert applications.thisyears_applications(u).exists()

        # Check that applications_for_camp agrees
        assert [app1] == list(applications.applications_for_camp(c1))
        assert [app2] == list(applications.applications_for_camp(c2))

        # Check that camps_for_application agrees
        assert [c1] == list(applications.camps_for_application(app1))
        assert [c2] == list(applications.camps_for_application(app2))

        # Check that thisyears_applications works if there are no future camps
        c2.delete()
        assert applications.thisyears_applications(u).exists()
