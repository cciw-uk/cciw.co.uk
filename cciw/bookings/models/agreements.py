from functools import lru_cache

from django.db import models
from django.utils import timezone


class CustomAgreementQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True)

    def for_year(self, year):
        return self.active().filter(year=year).order_by("sort_order")


CustomAgreementManager = models.Manager.from_queryset(CustomAgreementQuerySet)


class CustomAgreement(models.Model):
    """
    Defines an agreement that bookers must sign up to to confirm a booking.
    (in addition to standard ones)
    """

    # This was added to cover special situations where we need additional
    # agreements from bookers e.g. changes due to COVID-19

    # In particular, we may need to add these agreements after places have
    # already been booked, which complicates matters:
    #
    # - for places which haven't been booked, they need to see the
    #   additional conditions/agreements before booking, and be prevented
    #   from booking if agreements are missing (similar to the Booking.agreement
    #   field, but dynamically defined).
    #
    # - for places which have been booked, we need to obtain the additional
    #   agreement, but without "unbooking" or "unconfirming", because that
    #   would open an already booked place for someone else to take.

    # Currently, we only support applying this rule to an entire year of campers,
    # with some changes we could support specific camps perhaps.

    name = models.CharField(max_length=255, help_text="Appears as a title on 'Add place' page")
    year = models.IntegerField(help_text="Camp year this applies to")
    text_html = models.TextField(blank=False, help_text="Text of the agreement, in HTML format")
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    objects = CustomAgreementManager()

    class Meta:
        unique_together = [
            ["name", "year"],
        ]
        ordering = ["year", "sort_order"]

    def __str__(self):
        return f"{self.name} ({self.year})"


class AgreementFetcher:
    """
    Utility that looks up CustomAgreements, with caching
    to reduce queries for the patterns we use.
    """

    def __init__(self):
        # Per-instance caching:
        self.fetch = lru_cache(self.fetch)

    def fetch(self, *, year):
        return list(CustomAgreement.objects.for_year(year))
