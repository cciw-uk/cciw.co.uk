from bs4 import BeautifulSoup
from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.base import TestBase

from .models import Message

CONTACT_US_URL = reverse("cciw-contact_us-send")


class ContactUsPage(BasicSetupMixin, TestBase):

    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(
            html="\n<p>If you have an enquiry to make to the CCiW directors,\nplease use the form below and your message will be forwarded \nto the relevant person, who will reply by email.</p>\n",
            page_title="Christian Camps in Wales",
            name="contact_us_intro",
        )

        HtmlChunk.objects.create(name="contact_us_outro")

    def test_cant_send_without_email(self):
        self.client.post(CONTACT_US_URL, data=dict(name="My Name",
                                                   email="",
                                                   message="The Message",
                                                   cx_0="PASSED",
                                                   cx_1="PASSED",
                                                   subject="website"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Message.objects.count(), 0)

    def test_cant_send_without_valid_email(self):
        self.client.post(CONTACT_US_URL, data=dict(name="My Name",
                                                   email="invalidemail",
                                                   message="The Message",
                                                   cx_0="PASSED",
                                                   cx_1="PASSED",
                                                   subject="website"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Message.objects.count(), 0)

    def test_cant_send_without_message(self):
        self.client.post(CONTACT_US_URL, data=dict(name="My Name",
                                                   email="validemail@somewhere.com",
                                                   message="",
                                                   cx_0="PASSED",
                                                   cx_1="PASSED",
                                                   subject="website"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Message.objects.count(), 0)

    def test_form_appears(self):
        r = self.client.get(CONTACT_US_URL)
        b = BeautifulSoup(r.content, "lxml")
        self.assertNotEqual(b.find(name='input', attrs={'name': 'email'}), None)
        self.assertNotEqual(b.find(name='input', attrs={'name': 'name'}), None)
        self.assertNotEqual(b.find(name='textarea', attrs={'name': 'message'}), None)

    def test_send(self):
        self.client.post(CONTACT_US_URL, data=dict(name="My Name",
                                                   email="validemail@somewhere.com",
                                                   message="The Message",
                                                   cx_0="PASSED",
                                                   cx_1="PASSED",
                                                   subject="general"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(mail.outbox[0].to, settings.EMAIL_RECIPIENTS["GENERAL_CONTACT"])

    def test_send_to_booking_secretary(self):
        self.client.post(CONTACT_US_URL,
                         data=dict(name="My Name",
                                   email="validemail@somewhere.com",
                                   message="The Message",
                                   cx_0="PASSED",
                                   cx_1="PASSED",
                                   subject="bookings"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(sorted(mail.outbox[0].to),
                         sorted(settings.EMAIL_RECIPIENTS["BOOKING_SECRETARY"]))
        self.assertEqual(Message.objects.count(), 1)
