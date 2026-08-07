from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet, TextChoices
from django.utils import timezone

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp

# CRBs/DBSs - Criminal Records Bureau/Disclosure and Barring Service
#
# Related models and fields in the past were named 'CRB', and now renamed to
# 'DBS' for consistency with new DBS features. Older data was technically a CRB
# not DBS.


class DBSCheckManager(models.Manager):
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().select_related("officer")

    def get_for_camp(self, camp: Camp, *, include_late: bool = False) -> QuerySet:
        """
        Returns the DBSs that might be valid for a camp (ignoring the camp
        officer list)
        """
        # This logic is duplicated in cciw.officers.views.stats.

        # We include DBS applications that are after the camp date, for the sake
        # of the 'manage_dbss' function which might be used even after the camp
        # has run.
        qs = self.get_queryset().filter(completed_on__gte=camp.start_date - timedelta(settings.DBS_VALID_FOR))
        if not include_late:
            qs = qs.filter(completed_on__lte=camp.start_date)
        return qs


class DBSCheck(models.Model):
    class RequestedBy(models.TextChoices):
        CCIW = "CCIW", "CCiW"
        OTHER = "other", "Other organisation"
        UNKNOWN = "unknown", "Unknown"

    class CheckType(models.TextChoices):
        FORM = "form", "Full form"
        ONLINE = "online", "Online check"

    officer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="dbs_checks")
    dbs_number = models.CharField("Disclosure number", max_length=20)
    check_type = models.CharField("check type", max_length=20, choices=CheckType.choices, default=CheckType.FORM)
    completed_on = models.DateField(
        "Date of issue/check",
        help_text="For full forms, use the date of issue. For online checks, use the date of the check",
    )
    requested_by = models.CharField(
        max_length=20,
        choices=RequestedBy.choices,
        default=RequestedBy.UNKNOWN,
        help_text="The organisation that asked for this DBS to be done, normally CCiW.",
    )
    other_organisation = models.CharField(
        max_length=255, blank=True, help_text="If previous answer is not CCiW, please fill in"
    )
    applicant_accepted = models.BooleanField(
        default=True, help_text="Uncheck if the applicant could not be accepted on the basis of this DBS check"
    )

    registered_with_dbs_update = models.BooleanField("registered with DBS update service", null=True)

    objects = DBSCheckManager()

    def __str__(self):
        return f"DBS check for {self.officer.full_name}, {self.completed_on:%Y-%m-%d}"

    class Meta:
        verbose_name = "DBS/CRB check"
        verbose_name_plural = "DBS/CRB check"
        base_manager_name = "objects"

    def clean(self):
        if self.requested_by == DBSCheck.RequestedBy.OTHER and self.other_organisation.strip() == "":
            raise ValidationError(
                {"other_organisation": "This field is required if 'Requested by' is 'Other organisation'."}
            )

    def could_be_for_camp(self, camp: Camp) -> bool:
        return (
            self.completed_on >= camp.start_date - timedelta(days=settings.DBS_VALID_FOR)
            and self.completed_on <= camp.start_date
        )


class DBSActionLogType(TextChoices):
    FORM_SENT = "form_sent", "DBS form sent"
    LEADER_ALERT_SENT = "leader_alert_sent", "Alert sent to leader"
    REQUEST_FOR_DBS_FORM_SENT = "request_for_dbs_form_sent", "Request for DBS form sent"


class DBSActionLogManager(models.Manager):
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().select_related("officer")

    def create(self, *args, **kwargs) -> DBSActionLog:
        if "action_type" not in kwargs:
            raise TypeError("action_type is a required field")
        return super().create(*args, **kwargs)

    def remove_last(self, *, officer: User, action_type: DBSActionLogType) -> None:
        last = self.filter(officer=officer, action_type=action_type).order_by("-created_at").first()
        if last:
            last.delete()


class DBSActionLog(models.Model):
    """
    Represents a log of a DBS action done by DBS officer
    """

    officer = models.ForeignKey(User, related_name="dbsactionlogs", on_delete=models.PROTECT)
    action_type = models.CharField("action type", max_length=40, choices=DBSActionLogType)
    created_at = models.DateTimeField("Created at", default=timezone.now)
    user = models.ForeignKey(
        User,
        verbose_name="User who performed action",
        related_name="dbsactions_performed",
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
    )

    objects = DBSActionLogManager()

    class Meta:
        base_manager_name = "objects"
        verbose_name = "DBS action log"
        verbose_name_plural = "DBS action logs"

    def __str__(self):
        return f"Log of DBS action '{self.get_action_type_display()}' for {self.officer.full_name}, {self.created_at:%Y-%m-%d}"
