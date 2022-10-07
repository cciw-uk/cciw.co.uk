from django.urls import reverse

from cciw.cciwmain.tests import factories
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.base import TestBase


class SitePage(TestBase):
    def test_site_page(self):
        site = factories.create_site(short_name="My Lovely Site")
        response = self.client.get(site.get_absolute_url())
        assert response.status_code == 200

        self.assertContains(response, "My Lovely Site")

    def test_site_index_page(self):
        HtmlChunk.objects.get_or_create(name="sites_general")
        factories.create_site(long_name="My Lovely Site in the Valley")
        response = self.client.get(reverse("cciw-cciwmain-sites_index"))
        assert response.status_code == 200
        self.assertContains(response, "My Lovely Site in the Valley")
