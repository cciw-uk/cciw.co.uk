from django.test import TestCase

from cciw.cciwmain.tests.base import BasicSetupMixin


class HtmlChunkPage(BasicSetupMixin, TestCase):

    fixtures = ['users.json', 'htmlchunks.json']

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
        self.assertContains(response, '<p>CCIW is a charitable company')
        if should_see_edit_link:
            self.assertContains(response, "Edit home_page")
        else:
            self.assertNotContains(response, "Edit home_page")
