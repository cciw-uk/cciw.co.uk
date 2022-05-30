from django.db import models
from django.db.models import TextChoices
from django.utils import timezone

from cciw.bookings.models import BookingAccount


class MessageQuerySet(models.QuerySet):
    def older_than(self, before_datetime):
        return self.filter(created_at__lt=before_datetime)


class ContactType(TextChoices):
    WEBSITE = "website", "Web site problems"
    BOOKINGFORM = "bookingform", "Paper booking form request"
    BOOKINGS = "bookings", "Bookings"
    DATA_PROTECTION = "data_protection", "Data protection and related"
    VOLUNTEERING = "volunteering", "Volunteering"
    GENERAL = "general", "Other"


class Message(models.Model):
    subject = models.CharField(choices=ContactType.choices, max_length=max(map(len, ContactType.values)))
    email = models.EmailField("Email address")
    booking_account = models.ForeignKey(BookingAccount, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    objects = MessageQuerySet.as_manager()

    def __str__(self):
        return f"Message {self.id} from {self.email} on {self.created_at}"
