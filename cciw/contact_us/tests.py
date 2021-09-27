from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.webtest import WebTestBase

from .models import Message

CONTACT_US_URL = reverse("cciw-contact_us-send")


class ContactUsPage(BasicSetupMixin, WebTestBase):
    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(
            html="\n<p>If you have an enquiry to make to the CCiW directors,\nplease use the form below and your message will be forwarded \nto the relevant person, who will reply by email.</p>\n",
            page_title="Christian Camps in Wales",
            name="contact_us_intro",
        )

        HtmlChunk.objects.create(name="contact_us_outro")

    def test_cant_send_without_email(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_name": "My Name",
                "#id_email": "",
                "#id_message": "The Message",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 0
        assert Message.objects.count() == 0

    def test_cant_send_without_valid_email(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_name": "My Name",
                "#id_email": "invalidemail",
                "#id_message": "The Message",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 0
        assert Message.objects.count() == 0

    def test_cant_send_without_message(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_name": "My Name",
                "#id_email": "invalidemail",
                "#id_message": "",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 0
        assert Message.objects.count() == 0

    def test_send(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_name": "My Name",
                "#id_email": "validemail@example.com",
                "#id_message": "The Message",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 1
        assert Message.objects.count() == 1
        assert mail.outbox[0].to == settings.EMAIL_RECIPIENTS["GENERAL_CONTACT"]

    def test_send_to_booking_secretary(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_name": "My Name",
                "#id_email": "validemail@example.com",
                "#id_message": "The Message",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
                "#id_subject": "bookings",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 1
        assert sorted(mail.outbox[0].to) == sorted(settings.EMAIL_RECIPIENTS["BOOKING_SECRETARY"])
        assert Message.objects.count() == 1
