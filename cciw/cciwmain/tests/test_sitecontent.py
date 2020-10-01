# -*- coding: utf8 -*-

from django.contrib.auth.models import Permission

from cciw.accounts.models import User
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.sitecontent.models import MenuLink
from cciw.utils.tests.base import TestBase


class HtmlChunkPage(BasicSetupMixin, TestBase):

    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create(
            username="admin",
            first_name="Admin",
            last_name="",
            is_active=True,
            is_superuser=True,
            is_staff=True,
            email="someone@somewhere.com",
            password="plain$$test_admin_password",
        )
        self.editor_user = User.objects.create(
            username="editor",
            first_name="Editor",
            last_name="",
            is_active=True,
            is_superuser=False,
            is_staff=True,
            email="editor@somewhere.com",
            password="plain$$test_editor_password",
        )
        self.editor_user.user_permissions.add(
            Permission.objects.get_by_natural_key("add_htmlchunk", "sitecontent", "htmlchunk"),
            Permission.objects.get_by_natural_key("change_htmlchunk", "sitecontent", "htmlchunk"),
            Permission.objects.get_by_natural_key("delete_htmlchunk", "sitecontent", "htmlchunk"),
        )

        self.normal_user = User.objects.create(
            username="normaluser",
            first_name="Some other user",
            last_name="",
            is_active=True,
            is_superuser=False,
            is_staff=False,
            email="editor@somewhere.com",
            password="plain$$test_normaluser_password",
        )

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
        self.assertContains(response, '<p>CCiW is a charitable company')
        if should_see_edit_link:
            self.assertContains(response, "Edit home_page")
        else:
            self.assertNotContains(response, "Edit home_page")


class FindViewTests(BasicSetupMixin, TestBase):
    def test_find(self):
        menu_link = MenuLink.objects.create(title="Menu link title",
                                            listorder=0,
                                            url="/my-page/")
        menu_link.htmlchunk_set.create(
            name="my-page",
            html="<p>This is <b>my</b> page</p>",
            page_title="This is the page title",
        )
        response = self.client.get("/my-page/")
        self.assertContains(response, "This is the page title")
        self.assertContains(response, "This is <b>my</b> page")