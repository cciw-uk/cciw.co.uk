from BeautifulSoup import BeautifulSoup
from client import CciwClient
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core import mail

FEEDBACK_URL = reverse("cciwmain.misc.feedback")

class ContactUsPage(TestCase):
    fixtures = ['basic.yaml', 'contact.yaml']

    def setUp(self):
        self.client = CciwClient()

    def test_cant_send_without_email(self):
        self.client.post(FEEDBACK_URL, data = dict(name="My Name",
                                                   email="",
                                                   message="The Message"))
        self.assertEqual(len(mail.outbox), 0)

    def test_cant_send_without_valid_email(self):
        self.client.post(FEEDBACK_URL, data = dict(name="My Name",
                                                   email="invalidemail",
                                                   message="The Message"))
        self.assertEqual(len(mail.outbox), 0)

    def test_cant_send_without_message(self):
        self.client.post(FEEDBACK_URL, data = dict(name="My Name",
                                                   email="validemail@somewhere.com",
                                                   message=""))
        self.assertEqual(len(mail.outbox), 0)

    def test_form_appears(self):
        r = self.client.get(FEEDBACK_URL)
        b = BeautifulSoup(r.content)
        self.assertNotEqual(b.find(name='input', attrs={'name':'email'}), None)
        self.assertNotEqual(b.find(name='input', attrs={'name':'name'}), None)
        self.assertNotEqual(b.find(name='textarea', attrs={'name':'message'}), None)

    def test_send(self):
        self.client.post(FEEDBACK_URL, data = dict(name="My Name",
                                                   email="validemail@somewhere.com",
                                                   message="The Message"))
        self.assertEqual(len(mail.outbox), 1)
