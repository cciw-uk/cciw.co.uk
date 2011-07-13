"""
Utility functions for officers app.
"""
from datetime import date, datetime
from StringIO import StringIO

import xlwt

from cciw.officers.applications import applications_for_camp


def camp_officer_list(camp):
    """
    Returns complete list of officers for a camp
    """
    return list(camp.officers.all().order_by('first_name', 'last_name', 'email'))


def camp_slacker_list(camp):
    """
    Returns list of officers who have not filled out an application form
    """
    from cciw.officers.applications import applications_for_camp
    finished_apps_ids = applications_for_camp(camp).values_list('officer__id', flat=True)
    return list(camp.officers.order_by('first_name', 'last_name', 'email').exclude(id__in=finished_apps_ids))


def officer_data_to_xls(camp):
    # All the data we need:
    invites = camp.invitation_set.all().select_related('officer').order_by('officer__first_name',
                                                                           'officer__last_name')
    apps = applications_for_camp(camp)
    app_dict = dict((app.officer.id, app) for app in apps)

    # Attributes we need
    app_attr_getter = lambda attr: lambda user, inv, app: getattr(app, attr) if app is not None else ''
    columns = [('First name', lambda u, inv, app: u.first_name),
               ('Last name', lambda u, inv, app: u.last_name),
               ('E-mail', lambda u, inv, app: u.email),
               ('Notes', lambda u, inv, app: inv.notes),
               ('Address', app_attr_getter('address_firstline')),
               ('Town', app_attr_getter('address_town')),
               ('County', app_attr_getter('address_county')),
               ('Post code', app_attr_getter('address_postcode')),
               ('Country', app_attr_getter('address_country')),
               ('Tel', app_attr_getter('address_tel')),
               ('Mobile', app_attr_getter('address_mobile')),
               ('Birth date', app_attr_getter('birth_date')),
               ]

    wkbk = xlwt.Workbook(encoding='utf8')
    wksh = wkbk.add_sheet("Officers")

    # Headers:
    font_header = xlwt.Font()
    font_header.bold = True
    style_header = xlwt.XFStyle()
    style_header.font = font_header
    for c, (header, f) in enumerate(columns):
        wksh.write(0, c, header, style=style_header)

    # Data:
    date_style = xlwt.XFStyle()
    date_style.num_format_str = 'YYYY/MM/DD'
    for r, inv in enumerate(invites):
        user = inv.officer
        app = app_dict.get(user.id, None)
        for c, (header, f) in enumerate(columns):
            val = f(user, inv, app)
            if isinstance(val, (datetime, date)):
                style = date_style
            else:
                style = xlwt.Style.default_style
            wksh.write(r + 1, c, val, style=style)

    # Write out to string:
    s = StringIO()
    wkbk.save(s)
    s.seek(0)
    return s.read()
