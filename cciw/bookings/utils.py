import xlwt

from cciw.utils.xl import add_sheet_with_header_row, workbook_to_string

def camp_bookings_to_xls(camp):
    wkbk = xlwt.Workbook(encoding='utf8')
    columns = [('First name', lambda b: b.first_name),
               ('Last name', lambda b: b.last_name),
               ('Sex', lambda b: b.get_sex_display()),
               ('Date of birth', lambda b: b.date_of_birth),
               ('Age on camp', lambda b: b.age_on_camp().years),
               ('Address', lambda b: b.address),
               ]

    wksh_campers = add_sheet_with_header_row(wkbk,
                                             "Summary",
                                             [n for n, f in columns],
                                             [[f(b) for n, f in columns]
                                              for b in camp.bookings.confirmed().order_by('first_name', 'last_name')])
    return workbook_to_string(wkbk)


