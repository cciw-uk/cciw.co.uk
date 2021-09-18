from datetime import date, timedelta

from django.core import mail
from django.urls import reverse

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.base import factories as camps_factories
from cciw.officers import applications
from cciw.officers.models import Application
from cciw.officers.tests.base import (OFFICER, OFFICER_PASSWORD, OFFICER_USERNAME, CurrentCampsMixin,
                                      OfficersSetupMixin, RequireApplicationsMixin, RequireQualificationTypesMixin)
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import WebTestBase


class ApplicationModel(RequireApplicationsMixin, TestBase):

    def test_referees(self):
        for appid in [self.application1.id,
                      self.application2.id,
                      self.application3.id]:
            app = Application.objects.get(id=appid)
            assert app.referees[0] == app.referee_set.get(referee_number=1)
            assert app.referees[1] == app.referee_set.get(referee_number=2)


class PersonalApplicationList(CurrentCampsMixin, OfficersSetupMixin, RequireQualificationTypesMixin,
                              TestBase):

    _create_button = """<input type="submit" name="new" value="Create" """
    _edit_button = """<input type="submit" name="edit" value="Continue" """

    def setUp(self):
        super().setUp()
        self.client.login(username=OFFICER_USERNAME, password=OFFICER_PASSWORD)
        self.url = reverse('cciw-officers-applications')
        self.user = User.objects.get(username=OFFICER_USERNAME)
        self.user.applications.all().delete()

    def test_get(self):
        resp = self.client.get(self.url)
        assert 200 == resp.status_code
        self.assertContains(resp, "Your applications")

    def test_no_existing_application(self):
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)
        self.assertNotContains(resp, self._edit_button)

    def test_finished_application(self):
        self.user.applications.create(finished=True,
                                      date_saved=date.today() - timedelta(365))
        resp = self.client.get(self.url)
        self.assertContains(resp, self._create_button)

    def test_finished_application_recent(self):
        self.user.applications.create(finished=True,
                                      date_saved=date.today())
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)

    def test_unfinished_application(self):
        self.user.applications.create(finished=False,
                                      date_saved=date.today())
        resp = self.client.get(self.url)
        self.assertContains(resp, self._edit_button)

    def test_create_from_old(self):
        app = self.user.applications.create(finished=True,
                                            full_name="My Full Name",
                                            date_saved=date.today() - timedelta(365))
        ref, _ = app.referee_set.get_or_create(referee_number=1)
        ref.name = "Last Years Referee"
        ref.save()
        app.qualifications.create(
            type=self.first_aid_qualification,
            date_issued=date(2016, 1, 1))
        resp = self.client.post(self.url, {'new': 'Create'})
        assert 302 == resp.status_code
        assert len(self.user.applications.all()) == 2
        # New should be a copy of old:
        for a in self.user.applications.all():
            assert a.full_name == app.full_name
            assert a.referee_set.get(referee_number=1).name == \
                app.referee_set.get(referee_number=1).name
            assert list([q.type, q.date_issued] for q in a.qualifications.all()) == \
                list([q.type, q.date_issued] for q in app.qualifications.all())

    def test_create_when_already_done(self):
        # Should not create a new application if a recent one is submitted
        app = self.user.applications.create(finished=True,
                                            date_saved=date.today())
        resp = self.client.post(self.url, {'new': 'Create'})
        assert 200 == resp.status_code
        assert list(self.user.applications.all()) == [app]


class PersonalApplicationView(RequireApplicationsMixin, WebTestBase):
    def submit(self):
        super().submit('input[value="Get it"]')

    def test_view_txt(self):
        self.officer_login(OFFICER)
        self.get_url('cciw-officers-applications')
        self.fill({'#application': self.officer1.applications.all()[0].id,
                   '#format': 'txt'})
        self.submit()
        assert self.last_response.content_type == 'text/plain'
        assert b"Joe Winston Bloggs" in self.last_response.content

    def test_view_rtf(self):
        self.officer_login(OFFICER)
        self.get_url('cciw-officers-applications')
        self.fill({'#application': self.officer1.applications.all()[0].id,
                   '#format': 'rtf'})
        self.submit()
        assert self.last_response.content_type == 'text/rtf'
        assert b"\\cell Joe Winston Bloggs" in self.last_response.content

    def test_view_html(self):
        self.officer_login(OFFICER)
        self.get_url('cciw-officers-applications')
        self.fill({'#application': self.officer1.applications.all()[0].id,
                   '#format': 'html'})
        self.submit()
        self.assertTextPresent("Joe Winston Bloggs")

    def test_view_email(self):
        self.officer_login(OFFICER)
        self.get_url('cciw-officers-applications')
        self.fill({'#application': self.officer1.applications.filter(date_saved__year=2001)[0].id,
                   '#format': 'send'})
        self.submit()
        self.assertTextPresent("Email sent")

        m = mail.outbox[0]
        assert "Joe Winston Bloggs" in m.body
        fname, fdata, ftype = m.attachments[0]
        assert fname == "Application_joebloggs_2001-03-01.rtf"
        assert "\\cell Joe Winston Bloggs" in fdata
        assert ftype == "text/rtf"


class ApplicationUtils(BasicSetupMixin, TestBase):

    def test_date_saved_logic(self):

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

        Camp.objects.all().delete()
        c1 = camps_factories.create_camp(
            year=past_camp_start.year,
            start_date=past_camp_start,
        )
        c2 = camps_factories.create_camp(
            year=future_camp_start.year,
            start_date=future_camp_start,
        )
        u = User.objects.create(username='test')
        u.invitations.create(camp=c1)
        u.invitations.create(camp=c2)

        app1 = Application.objects.create(officer=u,
                                          finished=True,
                                          date_saved=past_camp_start - timedelta(1))

        # First, check we don't have any apps that are counted as 'this years'
        assert not applications.thisyears_applications(u).exists()

        # Create an application for this year
        app2 = Application.objects.create(officer=u,
                                          finished=True,
                                          date_saved=past_camp_start + timedelta(10))

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
