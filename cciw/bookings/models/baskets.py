from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .agreements import AgreementFetcher
from .bookings import Booking, BookingQuerySet
from .states import BookingState


@transaction.atomic
def book_basket_now(bookings_qs: BookingQuerySet):
    """
    Book a basket of bookings, returning True if successful,
    False otherwise.
    """
    bookings: list[Booking] = list(bookings_qs)

    now = timezone.now()
    fetcher = AgreementFetcher()
    for b in bookings:
        if any(p.blocker for p in b.get_booking_problems(agreement_fetcher=fetcher)):
            return False

    years = {b.camp.year for b in bookings}
    if len(years) != 1:
        raise AssertionError(f"Expected 1 year in basket, found {years}")

    # Serialize access to this function, to stop more places than available
    # being booked:
    year_bookings = Booking.objects.for_year(list(years)[0]).select_for_update()
    list(year_bookings)  # evaluate query to apply lock, don't need the result

    for b in bookings:
        b.booked_at = now
        # Early bird discounts are only applied for online bookings, and
        # this needs to be re-assessed if a booking expires and is later
        # booked again. Therefore it makes sense to put the logic here
        # rather than in the Booking model.
        b.early_bird_discount = b.can_have_early_bird_discount()
        b.auto_set_amount_due()
        b.state = BookingState.BOOKED
        b.booking_expires_at = now + timedelta(1)  # 24 hours
        b.save()

    # In some cases we may have enough money to pay for places from money in
    # account. Since a payment will not be needed or received, we need to
    # make sure these don't expire.
    seen_accounts = set()
    for b in bookings:
        if b.account_id in seen_accounts:
            continue
        b.account.distribute_balance()
        seen_accounts.add(b.account_id)

    return True
