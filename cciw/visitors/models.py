from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp


class VisitorLog(models.Model):
    """
    Log of a visitor being on a camp.
    """

    camp = models.ForeignKey(Camp, on_delete=models.PROTECT, related_name="visitor_logs")
    guest_name = models.CharField(verbose_name="name of guest", max_length=1024)
    arrived_on = models.DateField()
    left_on = models.DateField()
    purpose_of_visit = models.TextField()
    logged_at = models.DateTimeField(default=timezone.now)

    # To make it easy to log, we don't require authenticated login, so logged_by
    # is nullable
    logged_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    remote_addr = models.GenericIPAddressField()

    def __str__(self) -> str:
        return f"{self.guest_name} on {self.camp}, {self.arrived_on}"

    def clean(self) -> None:
        if self.left_on < self.arrived_on:
            raise ValidationError({"left_on": "'Left on' date must be on or after 'arrived on'"})
