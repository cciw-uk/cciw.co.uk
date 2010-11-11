from cciw.cciwmain.tests.client import CciwClient
from django.test import TestCase

class HtmlChunkPage(TestCase):
    fixtures = ['basic.yaml', 'users.yaml', 'htmlchunks.yaml']

    def setUp(self):
        self.client = CciwClient()

    def test_page_anonymous(self):
        self._test_page(False)

    def test_page_normal_user(self):
        self.assertTrue(self.client.login(username='normaluser', password='test_normaluser_password'))
        self._test_page(False)

    def test_page_editor(self):
        self.assertTrue(self.client.login(username='editor', password='test_editor_password'))
        self._test_page(True)

    def test_page_admin(self):
        self.assertTrue(self.client.login(username='admin', password='test_admin_password'))
        self._test_page(True)


    def _test_page(self, should_see_edit_link):
        response = self.client.get('/')
        self.assertTrue('<p>CCIW is a charitable company' in response.content,
                        "HtmlChunk not visible or not escaped properly")
        if should_see_edit_link:
            self.assertTrue("Edit home_page" in response.content,
                            "'Edit home page' link should be visible")
        else:
            self.assertTrue("Edit home_page" not in response.content,
                            "'Edit home page' link should not be visible")
