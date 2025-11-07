from django.db import models


class BookingState(models.TextChoices):
    INFO_COMPLETE = "info_complete", "Information complete"
    APPROVED = "approved", "Manually approved"
    BOOKED = "booked", "Booked"
    CANCELLED_DEPOSIT_KEPT = "cancelled_deposit_kept", "Cancelled - deposit kept"
    CANCELLED_HALF_REFUND = "cancelled_half_refund", "Cancelled - half refund (pre 2015 only)"
    CANCELLED_FULL_REFUND = "cancelled_full_refund", "Cancelled - full refund"
