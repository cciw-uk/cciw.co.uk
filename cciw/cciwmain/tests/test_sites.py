from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.tests.client import CciwClient
from cciw.cciwmain.models import Site
from cciw.sitecontent.models import HtmlChunk

class SitePage(TestCase):
    fixtures = ['basic.json', 'sites.json']

    def setUp(self):
        self.client = CciwClient()

    def test_site_page(self):
        site = Site.objects.get(id=1)
        response = self.client.get(site.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<address>Llys Andreas Camp Site")

    def test_site_index_page(self):
        HtmlChunk.objects.get_or_create(name="sites_general")
        response = self.client.get(reverse('cciwmain.sites.index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Llys Andreas, Barmouth")
