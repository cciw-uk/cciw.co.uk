from django.db import models
from django.utils import timezone

from cciw.bookings.models import BookingAccount


class Message(models.Model):
    email = models.EmailField("Email address")
    booking_account = models.ForeignKey(BookingAccount, null=True, blank=True)
    name = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
