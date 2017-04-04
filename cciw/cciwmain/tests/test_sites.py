from django.urls import reverse

from cciw.cciwmain.models import Site
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.base import TestBase


class SitePage(BasicSetupMixin, TestBase):

    def test_site_page(self):
        site = Site.objects.all()[0]
        response = self.client.get(site.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<address>Llys Andreas Camp Site")

    def test_site_index_page(self):
        HtmlChunk.objects.get_or_create(name="sites_general")
        response = self.client.get(reverse('cciw-cciwmain-sites_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Llys Andreas, Barmouth")
