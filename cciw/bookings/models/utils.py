from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.db.models import Func, Value, functions

if TYPE_CHECKING:
    from .bookings import Booking


class RegexpReplace(Func):
    function = "REGEXP_REPLACE"

    def __init__(self, expression, pattern, replacement, **extra):
        if not hasattr(pattern, "resolve_expression"):
            if not isinstance(pattern, str):
                raise TypeError("'pattern' must be a string")
            pattern = Value(pattern)
        if not hasattr(replacement, "resolve_expression"):
            if not isinstance(replacement, str):
                raise TypeError("'replacement' must be a string")
            replacement = Value(replacement)
        expressions = [expression, pattern, replacement]
        super().__init__(*expressions, **extra)


def sql_normalise_booking_name() -> Func:
    return sql_normalise_human_name_for_match(
        "first_name",
        Value(" "),
        "last_name",
    )


# People manage to use apostrophes in their names, and use them differently in subsequent years...
TO_SPACES_PATTERN = r"['’‘]"


def sql_normalise_human_name_for_match(*fields_or_values) -> Func:
    """
    Applies normalisation to a human name for matching purposes
    """
    # Strip multiple spaces plus leading/trailing.
    return functions.Lower(
        functions.Trim(
            functions.Replace(
                RegexpReplace(
                    functions.Concat(*fields_or_values),
                    TO_SPACES_PATTERN,
                    " ",
                ),
                Value("  "),
                Value(" "),
            ),
        )
    )


def normalise_booking_name(booking: Booking) -> str:
    # Python equivalent to sql_normalise_booking_name
    return normalise_human_name_for_match(booking.first_name, " ", booking.last_name)


def normalise_human_name_for_match(*values) -> str:
    # Python equivalent to sql_normalise_human_name_for_match
    return re.sub(
        TO_SPACES_PATTERN,
        " ",
        "".join(values).replace("  ", " ").strip().lower(),
    )
