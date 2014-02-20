from BeautifulSoup import BeautifulSoup
from cciw.cciwmain.tests.client import CciwClient
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail

CONTACT_US_URL = reverse("cciwmain.misc.contact_us")

class ContactUsPage(TestCase):
    fixtures = ['basic.json', 'contact.json']

    def setUp(self):
        self.client = CciwClient()

    def test_cant_send_without_email(self):
        self.client.post(CONTACT_US_URL, data = dict(name="My Name",
                                                     email="",
                                                     message="The Message",
                                                     subject="website"))
        self.assertEqual(len(mail.outbox), 0)

    def test_cant_send_without_valid_email(self):
        self.client.post(CONTACT_US_URL, data = dict(name="My Name",
                                                     email="invalidemail",
                                                     message="The Message",
                                                     subject="website"))
        self.assertEqual(len(mail.outbox), 0)

    def test_cant_send_without_message(self):
        self.client.post(CONTACT_US_URL, data = dict(name="My Name",
                                                     email="validemail@somewhere.com",
                                                     message="",
                                                     subject="website"))
        self.assertEqual(len(mail.outbox), 0)

    def test_form_appears(self):
        r = self.client.get(CONTACT_US_URL)
        b = BeautifulSoup(r.content)
        self.assertNotEqual(b.find(name='input', attrs={'name':'email'}), None)
        self.assertNotEqual(b.find(name='input', attrs={'name':'name'}), None)
        self.assertNotEqual(b.find(name='textarea', attrs={'name':'message'}), None)

    def test_send(self):
        self.client.post(CONTACT_US_URL, data = dict(name="My Name",
                                                     email="validemail@somewhere.com",
                                                     message="The Message",
                                                     subject="general"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.CONTACT_US_EMAIL])
        self.assertEqual(mail.outbox[0].extra_headers['Reply-To'], 'validemail@somewhere.com')

    def test_send_to_booking_secretary(self):
        self.client.post(CONTACT_US_URL,
                         data = dict(name="My Name",
                                     email="validemail@somewhere.com",
                                     message="The Message",
                                     subject="bookings"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(sorted(mail.outbox[0].to),
                         sorted([settings.BOOKING_SECRETARY_EMAIL,
                                 settings.CONTACT_US_EMAIL]))
