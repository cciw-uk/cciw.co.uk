from collections.abc import Callable
from datetime import date, timedelta
from itertools import groupby
from typing import Any

from dateutil.relativedelta import relativedelta
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

from cciw.cciwmain.models import Camp
from cciw.officers.applications import applications_for_camp
from cciw.utils.spreadsheet import ExcelSimpleBuilder

from .models import Booking, BookingAccount, Payment


def format_address(*args):
    return "\n".join(arg.strip() for arg in args)


def camp_bookings_to_spreadsheet(camp: Camp) -> ExcelSimpleBuilder:
    spreadsheet = ExcelSimpleBuilder()
    bookings = list(camp.bookings.confirmed().order_by("first_name", "last_name"))

    columns = [
        ("First name", lambda b: b.first_name),
        ("Last name", lambda b: b.last_name),
        ("Sex", lambda b: b.get_sex_display()),
        ("Date of birth", lambda b: b.birth_date),
        ("Age on camp", lambda b: b.age_on_camp()),
        ("Address", lambda b: b.get_address_display()),
        ("Email (camper)", lambda b: b.email),
        ("Email (account)", lambda b: b.account.email if b.account_id else None),
        ("Church", lambda b: b.church),
        ("Dietary requirements", lambda b: b.dietary_requirements),
        ("Booking date", lambda b: b.booked_at),
    ]

    spreadsheet.add_sheet_with_header_row(
        "Summary", [n for n, f in columns], [[f(b) for n, f in columns] for b in bookings]
    )

    everything_columns = [
        ("First name", lambda b: b.first_name),
        ("Last name", lambda b: b.last_name),
        ("Sex", lambda b: b.get_sex_display()),
        ("Date of birth", lambda b: b.birth_date),
        ("Age on camp", lambda b: b.age_on_camp()),
        ("Parent/guardian", lambda b: b.account.name),
        ("Contact phone number", lambda b: b.contact_phone_number),
        ("Contact address", lambda b: b.get_contact_address_display()),
        ("Church", lambda b: b.church),
        ("GP", lambda b: b.gp_name),
        ("GP address", lambda b: b.get_gp_address_display()),
        ("GP phone number", lambda b: b.gp_phone_number),
        ("NHS number", lambda b: b.medical_card_number),
        ("Last tetanus injection", lambda b: b.last_tetanus_injection_date),
        ("Allergies", lambda b: b.allergies),
        ("Medication", lambda b: b.regular_medication_required),
        ("Illnesses", lambda b: b.illnesses),
        ("Can swim 25m", lambda b: b.can_swim_25m),
        ("Learning difficulties", lambda b: b.learning_difficulties),
        ("Dietary requirements", lambda b: b.dietary_requirements),
        ("Publicity photos consent", lambda b: b.publicity_photos_agreement),
    ]

    spreadsheet.add_sheet_with_header_row(
        "Everything", [n for n, f in everything_columns], [[f(b) for n, f in everything_columns] for b in bookings]
    )

    def get_birthday(born):
        start = camp.start_date
        try:
            return born.replace(year=start.year)
        except ValueError:
            # raised when birth date is February 29 and the current year is not a leap year
            return born.replace(year=start.year, day=born.day - 1)

    bday_columns = [
        ("First name", lambda b: b.first_name),
        ("Last name", lambda b: b.last_name),
        ("Birthday", lambda b: get_birthday(b.birth_date).strftime("%A %d %B")),
        ("Age", lambda b: str(relativedelta(get_birthday(b.birth_date), b.birth_date).years)),
        ("Date of birth", lambda b: b.birth_date),
    ]

    bday_officer_columns = [
        lambda app: app.officer.first_name,
        lambda app: app.officer.last_name,
        lambda app: get_birthday(app.birth_date).strftime("%A %d %B"),
        lambda app: str(relativedelta(get_birthday(app.birth_date), app.birth_date).years),
        lambda app: app.birth_date,
    ]

    spreadsheet.add_sheet_with_header_row(
        "Birthdays on camp",
        [n for n, f in bday_columns],
        [
            [f(b) for n, f in bday_columns]
            for b in bookings
            if camp.start_date <= get_birthday(b.birth_date) <= camp.end_date
        ]
        + [
            [f(app) for f in bday_officer_columns]
            for app in applications_for_camp(camp)
            if camp.start_date <= get_birthday(app.birth_date) <= camp.end_date
        ],
    )

    return spreadsheet


def camp_sharable_transport_details_to_spreadsheet(camp: Camp):
    spreadsheet = ExcelSimpleBuilder()
    accounts = (
        BookingAccount.objects.filter(share_phone_number=True).filter(bookings__in=camp.bookings.confirmed()).distinct()
    )
    columns: list[tuple[str, Callable[[BookingAccount], Any]]] = [
        ("Name", lambda a: a.name),
        ("Post code", lambda a: a.address_post_code),
        ("Phone number", lambda a: a.phone_number),
        ("Email address", lambda a: a.email),
    ]

    spreadsheet.add_sheet_with_header_row(
        "Transport possibilities", [n for n, f in columns], [[f(b) for n, f in columns] for b in accounts]
    )
    return spreadsheet


# Spreadsheet needed by booking secretary
def year_bookings_to_spreadsheet(year: int) -> ExcelSimpleBuilder:
    spreadsheet = ExcelSimpleBuilder()
    bookings = (
        Booking.objects.filter(camp__year=year)
        .confirmed()
        .order_by("camp__camp_name__slug", "account__name", "first_name", "last_name")
        .select_related("camp", "camp__camp_name", "account")
    )

    columns = [
        ("Camp", lambda b: b.camp.name),
        ("Account", lambda b: b.account.name),
        ("First name", lambda b: b.first_name),
        ("Last name", lambda b: b.last_name),
        ("Sex", lambda b: b.get_sex_display()),
        ("DOB", lambda b: b.birth_date),
        ("Age", lambda b: b.age_on_camp()),
        ("Email (camper)", lambda b: b.email),
        ("Email (account)", lambda b: b.account.email if b.account_id else None),
        ("Date created", lambda b: b.created_at),
    ]

    spreadsheet.add_sheet_with_header_row(
        "All bookings", [n for n, f in columns], [[f(b) for n, f in columns] for b in bookings]
    )
    return spreadsheet


def payments_to_spreadsheet(date_start: date, date_end: date) -> ExcelSimpleBuilder:
    spreadsheet = ExcelSimpleBuilder()
    # Add one day to the date_end, since it is defined inclusively
    date_end = date_end + timedelta(days=1)

    payments = Payment.objects.filter(
        created_at__gte=date_start,
        created_at__lt=date_end,
        # Ignore payments with deleted source - these always
        # cancel out anyway:
        source__isnull=False,
    ).order_by("created_at")

    columns = [
        ("Account name", lambda p: p.account.name),
        ("Account email", lambda p: p.account.email),
        ("Amount", lambda p: p.amount),
        ("Date", lambda p: p.created_at),
        ("Type", lambda p: p.payment_type),
    ]

    spreadsheet.add_sheet_with_header_row(
        "Payments", [n for n, f in columns], [[f(p) for n, f in columns] for p in payments]
    )
    return spreadsheet


def addresses_for_mailing_list(year: int) -> ExcelSimpleBuilder:
    spreadsheet = ExcelSimpleBuilder()
    # We get the postal addresses that we have for the *previous* year
    # to generate the mailing list for the given year.
    bookings = (
        Booking.objects.filter(camp__year=year - 1)
        .order_by("account")  # for easy duplicate elimination
        .select_related("account")
    )

    headers = [
        "Name",
        "Address line 1",
        "Address line 2",
        "City",
        "County",
        "Country",
        "Post code",
        "Email",
        "Church",
        "# bookings",
        "URL",
    ]
    rows = []
    domain = get_current_site(None).domain

    link_start = f"https://{domain}"

    for account, acc_bookings in groupby(bookings, lambda b: b.account):
        if not account.include_in_mailings:
            continue

        acc_bookings = list(acc_bookings)
        if account.address_line1.strip() != "":
            # Account has postal address

            # Use booking data for church. It isn't important to be accurate,
            # this is just used to adjust mailing lists if a church is known to
            # already receive enough brochures.
            churches = [b.church.strip() for b in acc_bookings if b.church.strip()]
            church = churches[0] if churches else ""
            rows.append(
                [
                    account.name,
                    account.address_line1,
                    account.address_line2,
                    account.address_city,
                    account.address_county,
                    str(account.address_country.name),
                    account.address_post_code,
                    account.email,
                    church,
                    len(acc_bookings),
                    link_start + reverse("admin:bookings_bookingaccount_change", args=[account.id]),
                ]
            )
        else:
            # Use bookings for address

            # If they all have the same address, collapse
            first_booking = acc_bookings[0]
            if all(
                b.address_line1 == first_booking.address_line1
                and b.address_post_code == first_booking.address_post_code
                and b.address_line1 != ""
                for b in acc_bookings
            ):
                rows.append(
                    [
                        account.name,
                        first_booking.address_line1,
                        first_booking.address_line2,
                        first_booking.address_city,
                        first_booking.address_county,
                        str(first_booking.address_country.name),
                        first_booking.address_post_code,
                        account.email,
                        first_booking.church,
                        len(acc_bookings),
                        link_start + reverse("admin:bookings_booking_change", args=[first_booking.id]),
                    ]
                )
            else:
                for b in acc_bookings:
                    if b.address_line1 != "":
                        rows.append(
                            [
                                b.name,
                                b.address_line1,
                                b.address_line2,
                                b.address_city,
                                b.address_county,
                                str(b.address_country.name),
                                b.address_post_code,
                                b.get_contact_email(),
                                b.church,
                                1,
                                link_start + reverse("admin:bookings_booking_change", args=[b.id]),
                            ]
                        )
    rows.sort()  # first column (Name) alphabetical

    spreadsheet.add_sheet_with_header_row("Addresses", headers, rows)
    return spreadsheet
