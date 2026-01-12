from collections import defaultdict
from datetime import date

from django.db.models import Prefetch

from cciw.bookings.models.yearconfig import YearConfigFetcher
from cciw.cciwmain.models import Camp

from .bookings import Booking, Sex


def booking_report_by_camp(year: int) -> list[Camp]:
    """
    Returns list of camps with annotations:
      confirmed_bookings
      confirmed_bookings_boys
      confirmed_bookings_girls
    """
    camps = Camp.objects.filter(year=year).prefetch_related(
        Prefetch("bookings", queryset=Booking.objects.booked(), to_attr="confirmed_bookings"),
        Prefetch("bookings", queryset=Booking.objects.waiting_in_queue(), to_attr="waiting_in_queue_bookings"),
    )
    # Do some filtering in Python to avoid multiple db hits
    for c in camps:
        c.confirmed_bookings_boys = [b for b in c.confirmed_bookings if b.sex == Sex.MALE]
        c.confirmed_bookings_girls = [b for b in c.confirmed_bookings if b.sex == Sex.FEMALE]
        c.waiting_in_queue_bookings_boys = [b for b in c.waiting_in_queue_bookings if b.sex == Sex.MALE]
        c.waiting_in_queue_bookings_girls = [b for b in c.waiting_in_queue_bookings if b.sex == Sex.FEMALE]

    # MAYBE - do some DB aggregation to avoid actually pulling about Booking objects
    # when all we need is counts?

    return camps


def outstanding_bookings_with_fees(year: int) -> list[Booking]:
    """
    Returns bookings that have outstanding amounts due (or owed by us),
    with `calculated_balance` and `calculated_balance_due` annotations.
    """
    bookings = Booking.objects.for_year(year)
    # We need to include 'full refund' cancelled bookings in case they overpaid,
    # as well as all 'payable' bookings.
    bookings = bookings.payable() | bookings.cancelled()

    # 3 concerns:
    # 1) people who have overpaid. This must be calculated with respect to the total amount due
    #    on the account.
    # 2) people who have underpaid:
    #    a) with respect to the total amount now due
    #    b) with respect to the total amount due at this point in time,
    #       allowing for the fact that up to a certain point,
    #       only the deposit is actually required.
    #
    # TODO - can probably tidy this up now that deposits are remove.
    # People in group 2b) possibly need to be chased. They are not highlighted here - TODO

    bookings = bookings.order_by("account__name", "account__id", "first_name", "last_name")
    bookings = list(bookings.select_related("camp__camp_name", "account").prefetch_related("account__bookings__camp"))

    counts = defaultdict(int)
    for b in bookings:
        counts[b.account_id] += 1

    today = date.today()
    config_fetcher = YearConfigFetcher()

    outstanding = []
    for b in bookings:
        b.count_for_account = counts[b.account_id]
        if not hasattr(b.account, "calculated_balance"):
            b.account.calculated_balance = b.account.get_balance(today=None, config_fetcher=config_fetcher)
            b.account.calculated_balance_due = b.account.get_balance(today=today, config_fetcher=config_fetcher)

            if b.account.calculated_balance_due > 0 or b.account.calculated_balance < 0:
                outstanding.append(b)

    return outstanding
