from django.db import models
from django.utils import timezone

from cciw.accounts.models import User


class ErasureExecutionLog(models.Model):
    """
    Log of manually executed erasure request.
    """

    executed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    executed_at = models.DateTimeField(default=timezone.now, null=False, blank=False)
    plan_details = models.JSONField()  # From ErasurePlan

    def __str__(self):
        return str(self.executed_at)

    class Meta:
        ordering = ["executed_at"]
