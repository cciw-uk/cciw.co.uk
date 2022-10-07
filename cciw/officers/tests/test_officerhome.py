from django.urls import reverse

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.tests import factories as camp_factories
from cciw.utils.tests.webtest import WebTestBase

from . import factories


class OfficerHomePage(WebTestBase):
    def test_no_anonymous_access(self):
        self.get_url("cciw-officers-index")
        self.assertUrlsEqual(reverse("admin:login") + "?next=/officers/")

    def test_officer_access(self):
        self.officer_login(factories.create_officer())
        self.get_url("cciw-officers-index")
        self.assertCode(200)
        self.assertTextPresent("Submit/view applications")
        self.follow_link(f"a[href=\"{reverse('cciw-officers-applications')}\"]")

    def test_leader_access(self):
        camp_factories.create_camp(leader=(leader := factories.create_officer()))
        self.officer_login(leader)
        self.get_url("cciw-officers-index")
        self.assertCode(200)
        self.assertTextPresent("Tools for leaders")
        self.follow_link(f"a[href=\"{reverse('cciw-officers-leaders_index')}\"]")

    def test_booking_secretary_access(self):
        self.officer_login(factories.create_booking_secretary())
        self.get_url("cciw-officers-index")
        self.assertCode(200)
        self.assertTextPresent("Manage bookings")
        self.follow_link(f"a[href=\"{reverse('admin:app_list', args=('bookings',))}\"]")

    def test_dbs_officer_access(self):
        camp_factories.create_camp(future=True)
        self.officer_login(factories.create_dbs_officer())
        self.get_url("cciw-officers-index")
        self.assertCode(200)
        self.assertTextPresent("Manage DBSs")
        self.follow_link(f"a[href=\"{reverse('cciw-officers-manage_dbss', args=(get_thisyear(),))}\"]")
