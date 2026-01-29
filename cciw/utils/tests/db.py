from cciw.bookings.models.accounts import BookingAccount


def refresh(obj: BookingAccount) -> BookingAccount:
    return obj.__class__.objects.get(id=obj.id)
