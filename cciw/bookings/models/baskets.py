from .agreements import AgreementFetcher
from .bookings import Booking, BookingQuerySet


def add_basket_to_queue(bookings_qs: BookingQuerySet | list[Booking], *, by_account: bool = True):
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
        b.add_to_queue(by_account=by_account)

    return True
