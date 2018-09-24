"""
Utility functions for officers app.
"""
from collections import defaultdict


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
    from cciw.officers.models import Invitation, Application, Reference, DBSCheck

    officers = [i.officer for i in camp.invitations.all()]
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
                            date_saved__lte=latest_camp.start_date))

    all_received_refs = list(Reference.objects
                             .select_related('referee')
                             .filter(referee__application__in=all_apps))

    all_dbss = list(DBSCheck.objects.filter(officer__in=officers))

    received_ref_dict = defaultdict(list)
    for ref in all_received_refs:
        received_ref_dict[ref.referee.application_id].append(ref)

    # For each officer, we need to build a list of the years when they were on
    # camp but failed to submit an application form.

    # If they failed to submit two references, we also need to show them.  (If
    # they didn't submit an application form then they will definitely have
    # missing references).

    # Dictionaries containing officers as key, and a list of camps as values:
    officer_apps_missing = defaultdict(list)
    officer_apps_present = defaultdict(list)
    officer_refs_missing = defaultdict(list)
    officer_refs_present = defaultdict(list)
    officer_dbss_missing = defaultdict(list)
    officer_dbss_present = defaultdict(list)
    officer_apps_last_good_year = {}
    officer_refs_last_good_year = {}
    officer_dbss_last_good_year = {}

    for c in relevant_camps:
        camp_officers = set([i.officer
                             for i in all_invitations
                             if i.camp == c])
        camp_applications = [a for a in all_apps if a.could_be_for_camp(c)]
        officers_with_applications = set([a.officer for a in camp_applications])
        officers_with_two_references = set([a.officer for a in camp_applications
                                            if len(received_ref_dict[a.id]) >= 2])
        officers_with_dbss = set([dbs.officer for dbs in all_dbss if dbs.could_be_for_camp(c)])

        for o in camp_officers:
            if o in officers_with_applications:
                officer_apps_present[o].append(c)
            else:
                officer_apps_missing[o].append(c)
            if o in officers_with_two_references:
                officer_refs_present[o].append(c)
            else:
                officer_refs_missing[o].append(c)
            if o in officers_with_dbss:
                officer_dbss_present[o].append(c)
            else:
                officer_dbss_missing[o].append(c)

    # We only care about missing applications if they are not
    # followed by submitted applications i.e. an officer fixes
    # their past record by submitting one application.

    def sort_camps(camps):
        camps.sort(key=lambda camp: camp.start_date)

    def sort_camps_reverse(camps):
        camps.sort(key=lambda camp: camp.start_date, reverse=True)

    def get_missing_and_present_lists(present_dict, missing_dict, last_good_year_dict):
        for officer, camps in present_dict.items():
            if camps:
                sort_camps(camps)
                last_camp_with_item = camps[-1]
                missing_camps = missing_dict[officer]
                new_missing_camps = [
                    c for c in missing_camps
                    if c.start_date > last_camp_with_item.start_date
                ]
                missing_dict[officer] = new_missing_camps
                last_good_year_dict[officer] = last_camp_with_item.year

        for officer, camps in missing_dict.items():
            sort_camps_reverse(camps)

        # Don't show missing applications/references from current year
        for officer, camps in missing_dict.items():
            missing_dict[officer] = [c for c in camps if c.year < camp.year]

    get_missing_and_present_lists(officer_apps_present,
                                  officer_apps_missing,
                                  officer_apps_last_good_year)
    get_missing_and_present_lists(officer_refs_present,
                                  officer_refs_missing,
                                  officer_refs_last_good_year)
    get_missing_and_present_lists(officer_dbss_present,
                                  officer_dbss_missing,
                                  officer_dbss_last_good_year)

    tmp1 = [(o, officer_apps_missing[o], officer_refs_missing[o], officer_dbss_missing[o])
            for o in (set(officer_apps_missing.keys()) |
                      set(officer_refs_missing.keys()) |
                      set(officer_dbss_missing.keys()))
            ]
    # Remove empty items:
    tmp1 = [(o, a, r, c) for (o, a, r, c) in tmp1
            if len(a) > 0 or len(r) > 0 or len(c) > 0]
    return [{'officer': o,
             'missing_application_forms': a,
             'missing_references': r,
             'missing_dbss': c,
             'last_good_apps_year': officer_apps_last_good_year.get(o, None),
             'last_good_refs_year': officer_refs_last_good_year.get(o, None),
             'last_good_dbss_year': officer_dbss_last_good_year.get(o, None),
             } for o, a, r, c in tmp1]


def officer_data_to_spreadsheet(camp, spreadsheet):
    # Import here to avoid import cycle
    from cciw.officers.applications import applications_for_camp

    # All the data we need:
    invites = camp.invitations.all().select_related('officer').order_by('officer__first_name',
                                                                        'officer__last_name')
    apps = applications_for_camp(camp).prefetch_related('qualifications')
    app_dict = dict((app.officer.id, app) for app in apps)

    # Attributes we need
    app_attr_getter = lambda attr: lambda user, inv, app: getattr(app, attr) if app is not None else ''
    columns = [('First name', lambda u, inv, app: u.first_name),
               ('Last name', lambda u, inv, app: u.last_name),
               ('Email', lambda u, inv, app: u.email),
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

    header_row = [h for h, f in columns]

    def data_rows():
        for inv in invites:
            user = inv.officer
            app = app_dict.get(user.id, None)
            row = []
            for header, f in columns:
                row.append(f(user, inv, app))
            yield row

    spreadsheet.add_sheet_with_header_row("Officers", header_row, data_rows())

    # Qualifications sheet
    spreadsheet.add_sheet_with_header_row(
        "Qualifications",
        ["First name", "Last name", "Qualification", "Date issued"],
        [[a.officer.first_name, a.officer.last_name, q.type.name, q.date_issued]
         for a in apps
         for q in a.qualifications.all()]
    )
    return spreadsheet
