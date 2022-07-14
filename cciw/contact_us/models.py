from django.db import models
from django.db.models import TextChoices
from django.utils import timezone

from cciw.bookings.models import BookingAccount

from .bogofilter import BogofilterStatus, get_bogofilter_classification, make_email_msg, mark_ham, mark_spam


class MessageQuerySet(models.QuerySet):
    def older_than(self, before_datetime):
        return self.filter(created_at__lt=before_datetime)


class ContactType(TextChoices):
    WEBSITE = "website", "Web site problems"
    BOOKINGFORM = "bookingform", "Paper booking form request"
    BOOKINGS = "bookings", "Camp bookings and places"
    DATA_PROTECTION = "data_protection", "Data protection and related"
    VOLUNTEERING = "volunteering", "Volunteering"
    GENERAL = "general", "Other"


class SpamStatus(TextChoices):
    HAM = "HAM", "Ham"
    SPAM = "SPAM", "Spam"
    UNCLASSIFIED = "UNCLASSIFIED", "Unclassified"


class Message(models.Model):
    subject = models.CharField(choices=ContactType.choices, max_length=max(map(len, ContactType.values)))
    email = models.EmailField("Email address")
    booking_account = models.ForeignKey(BookingAccount, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    spam_classification_manual = models.CharField(
        verbose_name="Marked spam",
        max_length=12,
        choices=SpamStatus.choices,
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
    def bogosity_percent(self) -> int:
        return None if self.bogosity is None else int(self.bogosity * 100)

    def mark_spam(self):
        self.spam_classification_manual = SpamStatus.SPAM
        mark_spam(self._make_bogofilter_email_message())
        self.classify_with_bogofilter()

    def mark_ham(self):
        self.spam_classification_manual = SpamStatus.HAM
        mark_ham(self._make_bogofilter_email_message())
        self.classify_with_bogofilter()

    def classify_with_bogofilter(self) -> tuple[BogofilterStatus, float]:
        status, score = get_bogofilter_classification(self._make_bogofilter_email_message())
        if self.spam_classification_bogofilter == BogofilterStatus.UNCLASSIFIED or status != BogofilterStatus.ERROR:
            self.spam_classification_bogofilter = status
        if score is not None:
            self.bogosity = score
        self.save()
        return status, score

    def _make_bogofilter_email_message(self):
        return make_email_msg(
            self.email,
            self.get_subject_display(),
            self.message,
            extra_headers={"X-Account": repr(self.booking_account)} if self.booking_account else None,
        )
