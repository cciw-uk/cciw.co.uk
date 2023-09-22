from unittest import mock

from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.cciwmain.tests.base import SiteSetupMixin
from cciw.contact_us.bogofilter import BogofilterStatus
from cciw.officers.tests import factories as officer_factories
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.factories import Auto
from cciw.utils.tests.webtest import WebTestBase

from .models import ContactType, Message, SpamStatus


def create_message(message: str = Auto, subject: ContactType = ContactType.WEBSITE, email: str = Auto) -> Message:
    return Message.objects.create(
        subject=subject,
        email=email or "someemail@example.com",
        name="Some Person",
        message="This is an important message please read it" if message is Auto else message,
    )


CONTACT_US_URL = reverse("cciw-contact_us-send")


class ContactUsPage(WebTestBase):
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
                "#id_subject": "website",
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
                "#id_subject": "website",
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
                "#id_subject": "website",
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
                "#id_subject": "website",
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
        message = Message.objects.get()
        assert message.bogosity is not None
        assert message.spam_classification_bogofilter != BogofilterStatus.UNCLASSIFIED

    def test_send_to_booking_secretary(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_subject": "bookings",
                "#id_name": "My Name",
                "#id_email": "validemail@example.com",
                "#id_message": "The Message",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        self.submit('input[type="submit"]')
        assert len(mail.outbox) == 1
        assert sorted(mail.outbox[0].to) == sorted(settings.EMAIL_RECIPIENTS["BOOKING_SECRETARY"])
        assert Message.objects.count() == 1

    def test_spam_filter_threshold(self):
        self.get_url("cciw-contact_us-send")
        self.fill(
            {
                "#id_subject": "website",
                "#id_name": "Spam",
                "#id_email": "spammer@example.com",
                "#id_message": "Would you like some yummy Spam?",
                "#id_cx_0": "PASSED",
                "#id_cx_1": "PASSED",
            }
        )
        with mock.patch("cciw.contact_us.models.get_bogofilter_classification") as m:
            m.return_value = (BogofilterStatus.SPAM, 0.98)
            self.submit('input[type="submit"]')
        assert Message.objects.count() == 1
        assert len(mail.outbox) == 0


class ViewMessagePage(SiteSetupMixin, WebTestBase):
    def test_view(self):
        message = create_message()
        self.officer_login(officer_factories.create_secretary())
        self.get_url("cciw-contact_us-view", message.id)
        self.assertTextPresent(message.message)

    def test_ham_spam_buttons(self):
        message = create_message()
        assert message.spam_classification_manual == SpamStatus.UNCLASSIFIED
        self.officer_login(officer_factories.create_secretary())
        self.get_url("cciw-contact_us-view", message.id)

        self.submit('[name="mark_ham"]')
        self.assertTextPresent("Marked as ham")
        message.refresh_from_db()
        assert message.spam_classification_manual == SpamStatus.HAM

        self.submit('[name="mark_spam"]')
        self.assertTextPresent("Marked as spam")
        message.refresh_from_db()
        assert message.spam_classification_manual == SpamStatus.SPAM

    def test_reclassify(self):
        message = create_message(subject=ContactType.WEBSITE)
        self.officer_login(officer_factories.create_secretary())
        self.get_url("cciw-contact_us-view", message.id)
        self.fill({"#id_subject": ContactType.BOOKINGS})
        self.submit("[name=reclassify]")
        self.assertTextPresent(f"has been reclassified as '{ContactType.BOOKINGS.label}' and resent")
        assert len(mail.outbox) == 1
        assert sorted(mail.outbox[0].to) == sorted(settings.EMAIL_RECIPIENTS["BOOKING_SECRETARY"])
        assert Message.objects.count() == 1
