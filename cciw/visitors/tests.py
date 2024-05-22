from cciw.cciwmain.tests.factories import create_camp
from cciw.utils.tests.webtest import WebTestBase
from cciw.visitors.models import VisitorLog
from cciw.visitors.views import make_visitor_log_url


class VisitorsLogPage(WebTestBase):
    def test_fill_page(self):
        camp = create_camp()
        create_camp()  # a different one
        url = make_visitor_log_url(camp.year)
        self.get_literal_url(url)
        self.fill(
            {
                "#id_camp": str(camp.id),
                "#id_guest_name": "Peter Peterson",
                "#id_purpose_of_visit": "Just popped in",
            }
        )
        self.submit("input[type=submit]")
        assert VisitorLog.objects.count() == 1
        log = VisitorLog.objects.get()
        assert log.camp == camp

        self.assertTextPresent("You can add another entry")
        self.assertTextPresent("Just popped in", within="textarea")

        self.fill({"#id_guest_name": "Andrew Peterson"})
        self.submit("input[type=submit]")
        assert VisitorLog.objects.count() == 2

        assert [log.camp == camp for log in VisitorLog.objects.all()]
