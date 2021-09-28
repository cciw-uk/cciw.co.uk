from django.urls import reverse

from cciw.cciwmain.tests.base import factories as camps_factories
from cciw.officers.tests.base import factories
from cciw.utils.tests.webtest import WebTestBase


class ManageApplicationsPage(WebTestBase):
    def test_access_application(self):
        officer = factories.create_officer()
        application = factories.create_application(officer)
        camp = camps_factories.create_camp(leader=(leader := camps_factories.get_any_camp_leader()))
        factories.add_officers_to_camp(camp, [officer])

        self.officer_login(leader)
        self.get_url("cciw-officers-manage_applications", camp_id=camp.url_id)
        self.assertCode(200)
        self.fill({"#application": str(application.id)})
        self.submit('input[name="view"]')
        self.assertUrlsEqual(reverse("cciw-officers-view_application", kwargs=dict(application_id=application.id)))
        self.assertTextPresent(application.full_name)

    def test_view_by_non_leader(self):
        camp = camps_factories.create_camp()
        officer = factories.create_officer()
        self.officer_login(officer)
        self.get_literal_url(
            reverse("cciw-officers-manage_applications", kwargs=dict(camp_id=camp.url_id)), expect_errors=[403]
        )
        self.assertCode(403)
