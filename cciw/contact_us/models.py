import logging
from datetime import datetime

import mailer as queued_mail
from django.conf import settings
from django.db import models
from django.db.models import TextChoices
from django.urls import reverse
from django.utils import timezone

from cciw.bookings.models import BookingAccount
from cciw.cciwmain.common import get_current_domain

from .bogofilter import BogofilterStatus, get_bogofilter_classification, make_email_msg, mark_ham, mark_spam

logger = logging.getLogger(__name__)


class MessageQuerySet(models.QuerySet):
    def not_in_use(self, now: datetime):
        # The time period we put here is only relevant for manual erasure
        # requests. We therefore include all records, so that if requests for
        # erasure that come through the contact us page, we delete that request
        # message as well.
        return self.all()

    def older_than(self, before_datetime: datetime):
        return self.filter(created_at__lt=before_datetime)


class ContactType(TextChoices):
    WEBSITE = "website", "Web site problems"
    BOOKINGFORM = "bookingform", "Paper booking form request"
    BOOKINGS = "bookings", "Camp bookings and places"
    DATA_PROTECTION = "data_protection", "Data protection and related"
    VOLUNTEERING = "volunteering", "Volunteering"
    GENERAL = "general", "Other"


CONTACT_CHOICE_DESTS = {
    ContactType.BOOKINGFORM: settings.BOOKING_FORMS_EMAILS,
    ContactType.BOOKINGS: settings.BOOKING_SECRETARY_EMAILS,
    ContactType.GENERAL: settings.GENERAL_CONTACT_EMAILS,
    ContactType.WEBSITE: settings.WEBMASTER_EMAILS,
    ContactType.VOLUNTEERING: settings.VOLUNTEERING_EMAILS,
    ContactType.DATA_PROTECTION: settings.WEBMASTER_EMAILS,
}


for val in ContactType:
    assert val in CONTACT_CHOICE_DESTS, f"{val!r} missing form CONTACT_CHOICE_DESTS"


class SpamStatus(TextChoices):
    HAM = "HAM", "Ham"
    SPAM = "SPAM", "Spam"
    UNCLASSIFIED = "UNCLASSIFIED", "Unclassified"


class Message(models.Model):
    """
    Stores messages received from the "contact us" page.
    """

    subject = models.CharField(choices=ContactType, max_length=max(map(len, ContactType.values)))
    email = models.EmailField("Email address")
    booking_account = models.ForeignKey(BookingAccount, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    spam_classification_manual = models.CharField(
        verbose_name="Marked spam",
        max_length=12,
        choices=SpamStatus,
        default=SpamStatus.UNCLASSIFIED,
    )
    spam_classification_bogofilter = models.CharField(
        verbose_name="Bogofilter status",
        max_length=12,
        choices=BogofilterStatus.choices,
        default=BogofilterStatus.UNCLASSIFIED,
    )
    bogosity = models.FloatField(null=True, blank=True, default=None)

    objects = MessageQuerySet.as_manager()

    def __str__(self):
        return f"Message {self.id} from {self.email} on {self.created_at}"

    @property
    def bogosity_percent(self) -> int | None:
        return None if self.bogosity is None else int(self.bogosity * 100)

    def mark_spam(self):
        self.spam_classification_manual = SpamStatus.SPAM
        mark_spam(self._make_bogofilter_email_message())
        self.classify_with_bogofilter()

    def mark_ham(self):
        self.spam_classification_manual = SpamStatus.HAM
        mark_ham(self._make_bogofilter_email_message())
        self.classify_with_bogofilter()

    def classify_with_bogofilter(self) -> None:
        status, score = get_bogofilter_classification(self._make_bogofilter_email_message())
        if self.spam_classification_bogofilter == BogofilterStatus.UNCLASSIFIED or status != BogofilterStatus.ERROR:
            self.spam_classification_bogofilter = status
        if score is not None:
            self.bogosity = score
        self.save()

    def _make_bogofilter_email_message(self):
        return make_email_msg(
            self.email,
            self.get_subject_display(),
            self.message,
            extra_headers={"X-Account": repr(self.booking_account)} if self.booking_account else None,
        )

    def send_emails(self):
        if self.spam_classification_bogofilter == BogofilterStatus.SPAM and self.bogosity > 0.95:
            logger.info("Not sending contact_us email id=%s with spam score %.3f", self.id, self.bogosity)
            return

        to_emails = CONTACT_CHOICE_DESTS[self.subject]

        # Since msg.message could contain arbitrary spam, we don't send
        # it in an email (to protect our email server's spam reputation).
        # Instead we send a link to a page that will show the message.

        view_url = "https://{domain}{path}".format(
            domain=get_current_domain(), path=reverse("cciw-contact_us-view", args=(self.id,))
        )

        body = f"""
A message has been sent on the CCiW website feedback form, follow
the link to view it:

{view_url}

Spaminess: {self.bogosity_percent}% - {self.get_spam_classification_bogofilter_display().upper()}

    """

        queued_mail.send_mail(
            f"[CCIW] Website feedback {self.id}",
            body,
            settings.SERVER_EMAIL,
            to_emails,
        )
