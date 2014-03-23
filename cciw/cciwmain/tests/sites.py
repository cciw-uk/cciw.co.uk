from cciw.cciwmain.tests.client import CciwClient
from django.test import TestCase
from cciw.cciwmain.models import Site

class SitePage(TestCase):
    fixtures = ['basic.json', 'sites.json']

    def setUp(self):
        self.client = CciwClient()

    def test_site_page(self):
        site = Site.objects.get(id=1)
        response = self.client.get(site.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<address>Llys Andreas Camp Site")
