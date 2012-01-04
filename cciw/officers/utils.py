"""
Utility functions for officers app.
"""
import xlwt

from cciw.utils.xl import add_sheet_with_header_row, workbook_to_string


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
    # Import here to avoid import cycle when starting from handle_mail script
    from cciw.officers.applications import applications_for_camp

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
    header_row = [h for h,f in columns]
    def data_rows():
        for inv in invites:
            user = inv.officer
            app = app_dict.get(user.id, None)
            row = []
            for header, f in columns:
                row.append(f(user, inv, app))
            yield row

    add_sheet_with_header_row(wkbk, "Officers", header_row, data_rows())
    return workbook_to_string(wkbk)
