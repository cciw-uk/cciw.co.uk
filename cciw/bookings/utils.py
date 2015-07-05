from datetime import timedelta
from itertools import groupby

from dateutil.relativedelta import relativedelta

from cciw.bookings.models import Booking, Payment, BookingAccount
from cciw.officers.applications import applications_for_camp


def format_address(*args):
    return '\n'.join(arg.strip() for arg in args)


def camp_bookings_to_spreadsheet(camp, spreadsheet):
    bookings = list(camp.bookings.confirmed().order_by('first_name', 'last_name'))

    columns = [('First name', lambda b: b.first_name),
               ('Last name', lambda b: b.last_name),
               ('Sex', lambda b: b.get_sex_display()),
               ('Date of birth', lambda b: b.date_of_birth),
               ('Age on camp', lambda b: b.age_on_camp()),
               ('Address', lambda b: format_address(b.address, b.post_code)),
               ('Email', lambda b: b.get_contact_email()),
               ('Church', lambda b: b.church),
               ('Dietary requirements', lambda b: b.dietary_requirements),
               ('Booking date', lambda b: b.booked_at),
               ]

    spreadsheet.add_sheet_with_header_row("Summary",
                                          [n for n, f in columns],
                                          [[f(b) for n, f in columns]
                                           for b in bookings])

    everything_columns = \
        [('First name', lambda b: b.first_name),
         ('Last name', lambda b: b.last_name),
         ('Sex', lambda b: b.get_sex_display()),
         ('Date of birth', lambda b: b.date_of_birth),
         ('Age on camp', lambda b: b.age_on_camp()),
         ('Parent/guardian', lambda b: b.account.name),
         ('Contact phone number', lambda b: b.contact_phone_number),
         ('Contact address', lambda b: format_address(b.contact_address, b.contact_post_code)),
         ('Church', lambda b: b.church),
         ('GP', lambda b: b.gp_name),
         ('GP address', lambda b: b.gp_address),
         ('GP phone number', lambda b: b.gp_phone_number),
         ('Medical card number', lambda b: b.medical_card_number),
         ('Last tetanus injection', lambda b: b.last_tetanus_injection),
         ('Allergies', lambda b: b.allergies),
         ('Medication', lambda b: b.regular_medication_required),
         ('Illnesses', lambda b: b.illnesses),
         ('Can swim 25m', lambda b: b.can_swim_25m),
         ('Learning difficulties', lambda b: b.learning_difficulties),
         ('Dietary requirements', lambda b: b.dietary_requirements),
         ]

    spreadsheet.add_sheet_with_header_row("Everything",
                                          [n for n, f in everything_columns],
                                          [[f(b) for n, f in everything_columns]
                                           for b in bookings])

    def get_birthday(born):
        start = camp.start_date
        try:
            return born.replace(year=start.year)
        except ValueError:
            # raised when birth date is February 29 and the current year is not a leap year
            return born.replace(year=start.year, day=born.day - 1)

    bday_columns = [('First name', lambda b: b.first_name),
                    ('Last name', lambda b: b.last_name),
                    ('Birthday', lambda b: get_birthday(b.date_of_birth).strftime("%A %d %B")),
                    ('Age', lambda b: str(relativedelta(get_birthday(b.date_of_birth), b.date_of_birth).years)),
                    ('Date of birth', lambda b: b.date_of_birth)
                    ]

    bday_officer_columns = [lambda app: app.officer.first_name,
                            lambda app: app.officer.last_name,
                            lambda app: get_birthday(app.birth_date).strftime("%A %d %B"),
                            lambda app: str(relativedelta(get_birthday(app.birth_date), app.birth_date).years),
                            lambda app: app.birth_date,
                           ]


    spreadsheet.add_sheet_with_header_row("Birthdays on camp",
                                          [n for n, f in bday_columns],
                                          [[f(b) for n, f in bday_columns]
                                           for b in bookings if
                                           camp.start_date <= get_birthday(b.date_of_birth) <= camp.end_date] +
                                          [[f(app) for f in bday_officer_columns]
                                           for app in applications_for_camp(camp) if
                                           camp.start_date <= get_birthday(app.birth_date) <= camp.end_date])

    return spreadsheet.to_bytes()


def camp_sharable_transport_details_to_spreadsheet(camp, spreadsheet):
    accounts = (BookingAccount.objects
                .filter(share_phone_number=True)
                .filter(bookings__in=camp.bookings.confirmed())
                .distinct()
                )
    columns = [('Name', lambda a: a.name),
               ('Post code', lambda a: a.post_code),
               ('Phone number', lambda a: a.phone_number),
               ]

    spreadsheet.add_sheet_with_header_row("Transport possibilities",
                                          [n for n, f in columns],
                                          [[f(b) for n, f in columns]
                                           for b in accounts])
    return spreadsheet.to_bytes()


# Spreadsheet needed by booking secretary
def year_bookings_to_spreadsheet(year, spreadsheet):
    bookings = Booking.objects.filter(camp__year=year).order_by('camp__number', 'account__name', 'first_name', 'last_name').select_related('camp', 'account')

    columns = [
        ('Camp', lambda b: b.camp.number),
        ('Account', lambda b: b.account.name),
        ('First name', lambda b: b.first_name),
        ('Last name', lambda b: b.last_name),
        ('Sex', lambda b: b.get_sex_display()),
        ('Email', lambda b: b.get_contact_email()),
        ('State', lambda b: b.get_state_display()),
        ('Confirmed', lambda b: b.is_confirmed),
        ('Date created', lambda b: b.created),
    ]

    spreadsheet.add_sheet_with_header_row("All bookings",
                                          [n for n, f in columns],
                                          [[f(b) for n, f in columns]
                                           for b in bookings])
    return spreadsheet.to_bytes()


def payments_to_spreadsheet(date_start, date_end, spreadsheet):
    # Add one day to the date_end, since it is defined inclusively
    date_end = date_end + timedelta(days=1)

    payments = (Payment.objects
                .filter(created__gte=date_start,
                        created__lt=date_end)
                .select_related('account', 'origin_type')
                .prefetch_related('origin')
                .order_by('created')
                )

    from paypal.standard.ipn.models import PayPalIPN
    from cciw.bookings.models import ManualPayment, RefundPayment

    def get_payment_type(p):
        c = p.origin_type.model_class()
        if c is PayPalIPN:
            return 'PayPal'
        else:
            if p.origin is None:
                # Deleted
                return "(deleted)"
            v = p.origin.get_payment_type_display()
            if c is ManualPayment:
                return v
            elif c is RefundPayment:
                return "Refund " + v
            else:
                raise "Don't know what to do with %s" % c

    columns = [
        ('Account name', lambda p: p.account.name),
        ('Account email', lambda p: p.account.email),
        ('Amount', lambda p: p.amount),
        ('Date', lambda p: p.created),
        ('Type', get_payment_type),
    ]

    spreadsheet.add_sheet_with_header_row("Payments",
                                          [n for n, f in columns],
                                          [[f(p) for n, f in columns]
                                           for p in payments])
    return spreadsheet.to_bytes()


def addresses_for_mailing_list(year, spreadsheet):
    # We get the postal addresses that we have for the *previous* year
    # to generate the mailing list for the given year.
    bookings = (Booking.objects
                .filter(camp__year=year - 1)
                .order_by('account')  # for easy duplicate elimination
                .select_related('account')
                )

    headers = ['Name', 'Address', 'Post code', 'Email', '# bookings']
    rows = []
    for account, acc_bookings in groupby(bookings, lambda b: b.account):
        acc_bookings = list(acc_bookings)
        if account.address.strip() != "":
            # Account has postal address
            rows.append([account.name,
                         account.address,
                         account.post_code,
                         account.email,
                         len(acc_bookings)])
        else:
            # Use bookings for address

            # If they all have the same address, collapse
            first_booking = acc_bookings[0]
            if all(b.address == first_booking.address
                   and b.post_code == first_booking.post_code
                   for b in acc_bookings):
                rows.append([account.name,
                             first_booking.address,
                             first_booking.post_code,
                             account.email,
                             len(acc_bookings)])
            else:
                for b in acc_bookings:
                    rows.append([b.name,
                                 b.address,
                                 b.post_code,
                                 b.get_contact_email(),
                                 1])
    rows.sort()  # first column (Name) alphabetical

    spreadsheet.add_sheet_with_header_row("Addresses",
                                          headers,
                                          rows)
    return spreadsheet.to_bytes()
