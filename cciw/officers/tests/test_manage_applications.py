from django.urls import reverse

from cciw.cciwmain.tests.utils import set_thisyear
from cciw.officers.tests.base import LEADER, OFFICER, RequireApplicationsMixin
from cciw.utils.tests.webtest import WebTestBase


class ManageApplicationsPage(RequireApplicationsMixin, set_thisyear(2000), WebTestBase):
    def test_access_application(self):
        self.officer_login(LEADER)
        camp = self.default_camp_1
        self.get_url('cciw-officers-manage_applications', camp_id=camp.url_id)
        self.assertCode(200)
        self.fill({'#application': str(self.application1.id)})
        self.submit('input[name="view"]')
        self.assertUrlsEqual(reverse('cciw-officers-view_application',
                                     kwargs=dict(application_id=self.application1.id)))
        self.assertTextPresent(self.application1.full_name)

    def test_view_by_non_leader(self):
        self.officer_login(OFFICER)
        camp = self.default_camp_1
        self.get_literal_url(reverse('cciw-officers-manage_applications',
                                     kwargs=dict(camp_id=camp.url_id)),
                             expect_errors=[403])
        self.assertCode(403)
