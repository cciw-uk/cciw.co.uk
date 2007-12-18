from client import CciwClient
from django.test import TestCase
from cciw.cciwmain.models import Site

class SitePage(TestCase):    
    fixtures = ['basic.yaml', 'sites.yaml']

    def setUp(self):
        self.client = CciwClient()

    def test_site_page(self):
        site = Site.objects.get(id=1)
        response = self.client.get(site.get_absolute_url())
        self.failUnlessEqual(response.status_code, 200)

        self.assert_("<address>Llys Andreas Camp Site" in response.content,
                     "Site page not visible or content not escaped properly")

