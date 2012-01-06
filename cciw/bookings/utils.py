from dateutil.relativedelta import relativedelta
import xlwt

from cciw.utils.xl import add_sheet_with_header_row, workbook_to_string

def camp_bookings_to_xls(camp):
    bookings = list(camp.bookings.confirmed().order_by('first_name', 'last_name'))

    wkbk = xlwt.Workbook(encoding='utf8')
    columns = [('First name', lambda b: b.first_name),
               ('Last name', lambda b: b.last_name),
               ('Sex', lambda b: b.get_sex_display()),
               ('Date of birth', lambda b: b.date_of_birth),
               ('Age on camp', lambda b: b.age_on_camp().years),
               ('Address', lambda b: b.address),
               ('Church', lambda b: b.church),
               ('Dietary requirements', lambda b: b.dietary_requirements),
               ]

    wksh_campers = add_sheet_with_header_row(wkbk,
                                             "Summary",
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

    wksh_medical = add_sheet_with_header_row(wkbk,
                                             "Medical",
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


    wksh_bdays = add_sheet_with_header_row(wkbk,
                                           "Birthdays on camp",
                                           [n for n, f in bday_columns],
                                           [[f(b) for n, f in bday_columns]
                                            for b in bookings if
                                            camp.start_date <= get_birthday(b) <= camp.end_date])

    return workbook_to_string(wkbk)


