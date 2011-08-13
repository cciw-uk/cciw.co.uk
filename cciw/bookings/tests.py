from django.core.urlresolvers import reverse
from django.test import TestCase


class TestBookingStart(TestCase):

    fixtures = ['basic.json']

    def test_show_form(self):
        resp = self.client.get(reverse('cciw.bookings.views.start'))
        self.assertEqual(resp.status_code, 200)

        self.assertContains(resp, 'id_email')

