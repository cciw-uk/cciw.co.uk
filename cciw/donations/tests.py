from django.conf import settings
from django.core import mail

from cciw.bookings.factories import create_ipn
from cciw.bookings.models import Payment
from cciw.donations.views import DONATION_CUSTOM_VALUE
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.webtest import WebTestBase


class DonatePage(WebTestBase):
    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(name="donate_intro", html="Thank you for your interest in donating to CCiW")
        HtmlChunk.objects.create(name="donate_outro")

    def test_page(self):
        self.get_url("cciw-donations-donate")
        self.assertTextPresent("Thank you for your interest")
        self.fill({"#id_amount": 100})
        self.submit("[type=submit]")
        self.assertTextPresent("Redirecting")


def test_receive_donation(db):
    create_ipn(custom=DONATION_CUSTOM_VALUE, amount=100)
    assert Payment.objects.count() == 0
    assert len(mail.outbox) == 1
    (msg,) = mail.outbox
    assert "unrecognised" not in msg.subject
    assert msg.subject == "[CCIW] Donation received"
    assert "A donation was received" in msg.body
    assert msg.to == settings.EMAIL_RECIPIENTS["FINANCE"]
