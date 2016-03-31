from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from cciw.cciwmain.models import Camp, CampName, Site
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.officers import applications
from cciw.officers.models import Application
from cciw.officers.tests.base import (OFFICER_PASSWORD, OFFICER_USERNAME, ApplicationSetupMixin, CurrentCampsMixin,
                                      OfficersSetupMixin)
from cciw.utils.tests.base import TestBase

User = get_user_model()


class ApplicationModel(ApplicationSetupMixin, TestBase):

    def test_referees(self):
        for appid in [self.application1.id,
                      self.application2.id,
                      self.application3.id]:
            app = Application.objects.get(id=appid)
            self.assertEqual(app.referees[0], app.referee_set.get(referee_number=1))
            self.assertEqual(app.referees[1], app.referee_set.get(referee_number=2))


class PersonalApplicationList(CurrentCampsMixin, OfficersSetupMixin, TestBase):

    _create_button = """<input type="submit" name="new" value="Create" """
    _edit_button = """<input type="submit" name="edit" value="Continue" """

    def setUp(self):
        super(PersonalApplicationList, self).setUp()
        self.client.login(username=OFFICER_USERNAME, password=OFFICER_PASSWORD)
        self.url = reverse('cciw-officers-applications')
        self.user = User.objects.get(username=OFFICER_USERNAME)
        self.user.applications.all().delete()

    def test_get(self):
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)
        self.assertContains(resp, "Your applications")

    def test_no_existing_application(self):
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)
        self.assertNotContains(resp, self._edit_button)

    def test_finished_application(self):
        self.user.applications.create(finished=True,
                                      date_submitted=date.today() - timedelta(365))
        resp = self.client.get(self.url)
        self.assertContains(resp, self._create_button)

    def test_finished_application_recent(self):
        self.user.applications.create(finished=True,
                                      date_submitted=date.today())
        resp = self.client.get(self.url)
        self.assertNotContains(resp, self._create_button)

    def test_unfinished_application(self):
        self.user.applications.create(finished=False,
                                      date_submitted=date.today())
        resp = self.client.get(self.url)
        self.assertContains(resp, self._edit_button)

    def test_create(self):
        app = self.user.applications.create(finished=True,
                                            full_name="My Full Name",
                                            date_submitted=date.today() - timedelta(365))
        ref, _ = app.referee_set.get_or_create(referee_number=1)
        ref.name = "Last Years Referee"
        ref.save()
        resp = self.client.post(self.url, {'new': 'Create'})
        self.assertEqual(302, resp.status_code)
        self.assertEqual(len(self.user.applications.all()), 2)
        # New should be a copy of old:
        for a in self.user.applications.all():
            self.assertEqual(a.full_name, app.full_name)
            self.assertEqual(a.referee_set.get(referee_number=1).name,
                             app.referee_set.get(referee_number=1).name)

    def test_create_when_already_done(self):
        # Should not create a new application if a recent one is submitted
        app = self.user.applications.create(finished=True,
                                            date_submitted=date.today())
        resp = self.client.post(self.url, {'new': 'Create'})
        self.assertEqual(200, resp.status_code)
        self.assertEqual(list(self.user.applications.all()), [app])


class ApplicationUtils(BasicSetupMixin, TestBase):

    def test_date_submitted_logic(self):

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

        camp_name, _ = CampName.objects.get_or_create(
            name="Blue",
            slug="blue",
            color="#0000ff",
        )

        site = Site.objects.first()
        Camp.objects.all().delete()
        c1 = Camp.objects.create(year=past_camp_start.year,
                                 camp_name=camp_name,
                                 start_date=past_camp_start,
                                 end_date=past_camp_start + timedelta(7),
                                 minimum_age=11, maximum_age=17,
                                 site=site)
        c2 = Camp.objects.create(year=future_camp_start.year,
                                 camp_name=camp_name,
                                 start_date=future_camp_start,
                                 end_date=future_camp_start + timedelta(7),
                                 minimum_age=11, maximum_age=17,
                                 site=site)

        u = User.objects.create(username='test')
        u.invitations.create(camp=c1)
        u.invitations.create(camp=c2)

        app1 = Application.objects.create(officer=u,
                                          finished=True,
                                          date_submitted=past_camp_start - timedelta(1))

        # First, check we don't have any apps that are counted as 'this years'
        self.assertFalse(applications.thisyears_applications(u).exists())

        # Create an application for this year
        app2 = Application.objects.create(officer=u,
                                          finished=True,
                                          date_submitted=past_camp_start + timedelta(10))

        # Now we should have one
        self.assertTrue(applications.thisyears_applications(u).exists())

        # Check that applications_for_camp agrees
        self.assertEqual([app1], list(applications.applications_for_camp(c1)))
        self.assertEqual([app2], list(applications.applications_for_camp(c2)))

        # Check that camps_for_application agrees
        self.assertEqual([c1], list(applications.camps_for_application(app1)))
        self.assertEqual([c2], list(applications.camps_for_application(app2)))

        # Check that thisyears_applications works if there are no future camps
        c2.delete()
        self.assertTrue(applications.thisyears_applications(u).exists())
