from dateutil.relativedelta import relativedelta

from cciw.bookings.models import Booking


def camp_bookings_to_spreadsheet(camp, spreadsheet):
    bookings = list(camp.bookings.confirmed().order_by('first_name', 'last_name'))

    columns = [('First name', lambda b: b.first_name),
               ('Last name', lambda b: b.last_name),
               ('Sex', lambda b: b.get_sex_display()),
               ('Date of birth', lambda b: b.date_of_birth),
               ('Age on camp', lambda b: b.age_on_camp().years),
               ('Address', lambda b: b.address),
               ('Church', lambda b: b.church),
               ('Dietary requirements', lambda b: b.dietary_requirements),
               ]

    spreadsheet.add_sheet_with_header_row("Summary",
                                          [n for n, f in columns],
                                          [[f(b) for n, f in columns]
                                           for b in bookings])

    medical_columns = \
        [('First name', lambda b: b.first_name),
         ('Last name', lambda b: b.last_name),
         ('Sex', lambda b: b.get_sex_display()),
         ('Date of birth', lambda b: b.date_of_birth),
         ('Parent/guardian', lambda b: b.account.name),
         ('Contact phone number', lambda b: b.contact_phone_number),
         ('Contact address', lambda b: b.contact_address + ((u'\n' + b.contact_post_code) if
                                                            b.contact_post_code else '')),
         ('GP', lambda b: b.gp_name),
         ('GP phone number', lambda b: b.gp_phone_number),
         ('Medical card number', lambda b: b.medical_card_number),
         ('Last tetanus injection', lambda b: b.last_tetanus_injection),
         ('Allergies', lambda b: b.allergies),
         ('Medication', lambda b: b.regular_medication_required),
         ('Illnesses', lambda b: b.illnesses),
         ('Learning difficulties', lambda b: b.learning_difficulties),
         ]

    spreadsheet.add_sheet_with_header_row("Medical",
                                          [n for n, f in medical_columns],
                                          [[f(b) for n, f in medical_columns]
                                           for b in bookings])

    def get_birthday(b):
        start = camp.start_date
        born = b.date_of_birth
        try:
            return born.replace(year=start.year)
        except ValueError:
            # raised when birth date is February 29 and the current year is not a leap year
            return born.replace(year=start.year, day=born.day - 1)

    bday_columns = [('First name', lambda b: b.first_name),
                    ('Last name', lambda b: b.last_name),
                    ('Birthday', lambda b: get_birthday(b).strftime("%A %d %B")),
                    ('Age', lambda b: unicode(relativedelta(get_birthday(b), b.date_of_birth).years)),
                    ('Date of birth', lambda b: b.date_of_birth)
                    ]


    spreadsheet.add_sheet_with_header_row("Birthdays on camp",
                                          [n for n, f in bday_columns],
                                          [[f(b) for n, f in bday_columns]
                                           for b in bookings if
                                           camp.start_date <= get_birthday(b) <= camp.end_date])

    return spreadsheet.to_string()


# Spreadsheet needed by booking secretary
def year_bookings_to_spreadsheet(year, spreadsheet):
    bookings = Booking.objects.filter(camp__year=year).order_by('camp__number', 'account__name', 'first_name', 'last_name').select_related('camp', 'account')

    columns = [
        ('Camp', lambda b: b.camp.number),
        ('Account', lambda b: b.account.name),
        ('First name', lambda b: b.first_name),
        ('Last name', lambda b: b.last_name),
        ('Sex', lambda b: b.get_sex_display()),
        ('State', lambda b: b.get_state_display()),
        ('Confirmed', lambda b: b.confirmed_booking()),
        ('Date created', lambda b: b.created),
        ]

    spreadsheet.add_sheet_with_header_row("All bookings",
                                          [n for n, f in columns],
                                          [[f(b) for n, f in columns]
                                           for b in bookings])
    return spreadsheet.to_string()
