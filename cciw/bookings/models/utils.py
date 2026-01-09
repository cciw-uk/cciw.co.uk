from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Value, functions

if TYPE_CHECKING:
    from .bookings import Booking


def sql_normalise_booking_name():
    return sql_normalise_human_name_for_match(
        "first_name",
        Value(" "),
        "last_name",
    )


def sql_normalise_human_name_for_match(*fields_or_values):
    """
    Applies normalisation to a human name for matching purposes
    """
    # Strip multiple spaces plus leading/trailing.
    return functions.Lower(
        functions.Trim(functions.Replace(functions.Concat(*fields_or_values), Value("  "), Value(" ")))
    )


def normalise_booking_name(booking: Booking) -> str:
    # Python equivalent to sql_normalise_booking_name
    return normalise_human_name_for_match(booking.first_name, " ", booking.last_name)


def normalise_human_name_for_match(*values) -> str:
    # Python equivalent to sql_normalise_human_name_for_match
    return "".join(values).replace("  ", " ").strip().lower()
