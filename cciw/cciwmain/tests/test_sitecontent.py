from cciw.officers.tests import factories
from cciw.sitecontent.models import HtmlChunk, MenuLink
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import WebTestBase


class HtmlChunkPage(WebTestBase):
    def test_page_anonymous(self):
        self._test_page(should_see_edit_link=False)

    def test_page_normal_user(self):
        self.officer_login(factories.create_officer())
        self._test_page(should_see_edit_link=False)

    def test_page_editor(self):
        self.officer_login(factories.create_site_editor())
        self._test_page(should_see_edit_link=True)

    def test_page_admin(self):
        self.officer_login(factories.create_officer(is_superuser=True))
        self._test_page(should_see_edit_link=True)

    def _test_page(self, *, should_see_edit_link: bool):
        m = MenuLink.objects.create(visible=True, extra_title="", parent_item=None, title="Home", url="/", listorder=0)

        HtmlChunk.objects.create(
            menu_link=m,
            html="<p>CCiW is a charitable company...</p>",
            page_title="Christian Camps in Wales",
            name="home_page",
        )
        self.get_literal_url("/")
        self.assertTextPresent("CCiW is a charitable company")
        if should_see_edit_link:
            self.assertTextPresent("Edit home_page")
        else:
            self.assertTextAbsent("Edit home_page")


class FindViewTests(TestBase):
    def test_find(self):
        menu_link = MenuLink.objects.create(title="Menu link title", listorder=0, url="/my-page/")
        menu_link.htmlchunk_set.create(
            name="my-page",
            html="<p>This is <b>my</b> page</p>",
            page_title="This is the page title",
        )
        response = self.client.get("/my-page/")
        self.assertContains(response, "This is the page title")
        self.assertContains(response, "This is <b>my</b> page")
