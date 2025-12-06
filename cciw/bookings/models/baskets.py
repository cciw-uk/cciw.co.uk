from django.utils import timezone

from .agreements import AgreementFetcher
from .bookings import Booking, BookingQuerySet
from .states import BookingState


def book_bookings_now(bookings_qs: BookingQuerySet | list[Booking]):
    """
    Book a group of bookings.
    """
    # TODO #52 - this is used by tests currently,
    # we probably want something that operates on BookingQueueEntry objects
    # and changes the `state` value.
    bookings: list[Booking] = list(bookings_qs)

    now = timezone.now()

    for b in bookings:
        b.booked_at = now
        # Early bird discounts are only applied for online bookings, and
        # this needs to be re-assessed if a booking expires and is later
        # booked again. Therefore it makes sense to put the logic here
        # rather than in the Booking model.
        b.early_bird_discount = b.can_have_early_bird_discount()
        b.auto_set_amount_due()
        b.state = BookingState.BOOKED
        b.save()

    return True


def add_basket_to_queue(bookings_qs: BookingQuerySet | list[Booking]):
    """
    Add a basket of bookings to the queue, returning True if successful,
    False otherwise.
    """
    bookings: list[Booking] = list(bookings_qs)

    fetcher = AgreementFetcher()
    for b in bookings:
        if any(p.blocker for p in b.get_booking_problems(agreement_fetcher=fetcher)):
            return False

    years = {b.camp.year for b in bookings}
    if len(years) != 1:
        raise AssertionError(f"Expected 1 year in basket, found {years}")

    for b in bookings:
        b.add_to_queue()

    return True
