"""
Utility functions for officers app.
"""
from collections import defaultdict
from datetime import datetime

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


def camp_serious_slacker_list(camp):
    """
    Returns a list of officers who have serious problems in terms
    of submitted applications and references.
    """
    # This looks at history - so we find officers who have been on camps before.
    # We also look across all the camps, to catch officers who might go from one
    # camp to the next, never submitting application forms or references.  This
    # means the logic is slightly different than 'applications_for_camp', but as
    # this is meant as a warning system it doesn't matter that it doesn't match
    # the logic exactly.


    from cciw.cciwmain.models import Camp
    from cciw.officers.models import Invitation, Application, Reference

    officers = [i.officer for i in camp.invitation_set.all()]
    # We need to allow applications/references for the current year to 'fix' a
    # track record. However, when displaying past problems, don't include the
    # current year.
    relevant_camps = list(Camp.objects
                          .filter(year__lte=camp.start_date.year)
                          .order_by('-start_date'))

    if len(relevant_camps) == 0:
        return []

    latest_camp = relevant_camps[0]

    all_invitations = list(Invitation.objects
                           .filter(camp__in=relevant_camps,
                                   officer__in=officers)
                           .select_related('camp', 'officer'))
    all_apps = list(Application.objects
                    .filter(finished=True,
                            officer__in=officers,
                            date_submitted__lte=latest_camp.start_date))

    # For each officer, we need to build a list of the years when they were on
    # camp but failed to submit an application form.

    # Dictionaries containing officers as key, and a list of camps as values:
    officer_apps_missing = defaultdict(list)
    officer_apps_present = defaultdict(list)

    for c in relevant_camps:
        camp_officers = set([i.officer
                             for i in all_invitations
                             if i.camp == c])
        officers_with_applications = set([a.officer
                                          for a in all_apps
                                          if a.could_be_for_camp(c)
                                          and a.officer in camp_officers])

        for o in camp_officers:
            if o in officers_with_applications:
                officer_apps_present[o].append(c)
            else:
                officer_apps_missing[o].append(c)

    # We only care about missing applications if they are not
    # followed by submitted applications i.e. an officer fixes
    # their past record by submitting one application.

    for officer, camps in officer_apps_present.items():
        if camps:
            camps.sort(key=lambda camp:camp.start_date)
            last_camp_with_app = camps[-1]
            missing_camps = officer_apps_missing[officer]
            new_missing_camps = [
                c for c in missing_camps
                if c.start_date > last_camp_with_app.start_date
            ]
            new_missing_camps.sort(key=lambda camp:camp.start_date)
            officer_apps_missing[officer] = new_missing_camps

    for officer, camps in officer_apps_missing.items():
        officer_apps_missing[officer] = [c for c in camps if c.year < camp.year]

    return [{'officer': o,
             'missing_application_forms': camps
            } for o, camps in officer_apps_missing.items() if camps]


def officer_data_to_spreadsheet(camp, spreadsheet):
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

    header_row = [h for h,f in columns]
    def data_rows():
        for inv in invites:
            user = inv.officer
            app = app_dict.get(user.id, None)
            row = []
            for header, f in columns:
                row.append(f(user, inv, app))
            yield row

    spreadsheet.add_sheet_with_header_row("Officers", header_row, data_rows())
    return spreadsheet.to_string()
