from datetime import date, datetime, timedelta

from django.db import models
from django.utils import timezone

from cciw.documents.fields import DocumentField
from cciw.documents.models import Document, DocumentManager, DocumentQuerySet

from .bookings import Booking
from .constants import KEEP_FINANCIAL_RECORDS_FOR


class SupportingInformationType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class SupportingInformationDocumentQuerySet(DocumentQuerySet):
    def orphaned(self):
        return self.filter(supporting_information__isnull=True)

    def old(self):
        return self.filter(created_at__lt=timezone.now() - timedelta(days=1))

    def for_year(self, year):
        return self.filter(supporting_information__booking__camp__year=year)

    def not_in_use(self, now: datetime):
        return self.filter(created_at__lt=now - KEEP_FINANCIAL_RECORDS_FOR)


SupportingInformationDocumentManager = DocumentManager.from_queryset(SupportingInformationDocumentQuerySet)


class SupportingInformationDocument(Document):
    """
    Stores the (optional) uploaded document associated with "SupportingInformation"
    """

    objects = SupportingInformationDocumentManager()

    class Meta:
        # to ensure we get our 'defer' behaviour for `SupportingInformation.document` access:
        base_manager_name = "objects"
        # (Note this doesn't work for things like `select_related("document")`,
        # we have to explicitly add `defer("document__content")` sometimes)

    def __str__(self):
        if getattr(self, "supporting_information", None) is None:
            return f"{self.filename} <orphaned>"
        return f"{self.filename}, relating to booking {self.supporting_information.booking}"


class SupportingInformationQuerySet(models.QuerySet):
    def for_year(self, year):
        return self.filter(booking__camp__year=year)

    def older_than(self, before_datetime):
        return self.filter(created_at__lt=before_datetime)

    def not_in_use(self, now: datetime):
        return self.filter(received_on__lt=now - KEEP_FINANCIAL_RECORDS_FOR)


SupportingInformationManager = models.Manager.from_queryset(SupportingInformationQuerySet)


class SupportingInformation(models.Model):
    """
    Supporting information used to assess a booking or request for booking
    discount.
    """

    booking = models.ForeignKey(Booking, related_name="supporting_information_records", on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    received_on = models.DateField("date received", default=date.today)
    information_type = models.ForeignKey(SupportingInformationType, on_delete=models.PROTECT)
    from_name = models.CharField(max_length=100, help_text="Name of person or organisation the information is from")
    from_email = models.EmailField(blank=True)
    from_telephone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    document = DocumentField(
        SupportingInformationDocument,
        related_name="supporting_information",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
    )
    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SupportingInformationManager()

    def __str__(self):
        return f"{self.information_type.name} for {self.booking}"

    def save(self, **kwargs):
        super().save(**kwargs)
        # This is needed for SupportingInformationForm to work in all contexts
        # in admin, because ModelForm.save() is called with `commit=False`
        # sometimes.
        if self.document is not None:
            doc_save_kwargs = kwargs.copy()
            doc_save_kwargs["force_insert"] = False
            self.document.save(**doc_save_kwargs)

    class Meta:
        verbose_name = "supporting information record"
        verbose_name_plural = "supporting information records"
