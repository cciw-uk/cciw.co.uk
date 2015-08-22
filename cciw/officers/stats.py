from datetime import date, timedelta

import pandas as pd
from django.conf import settings

from cciw.officers.applications import applications_for_camp
from cciw.officers.models import ReferenceForm, CRBApplication


def get_camp_officer_stats(camp):
    # For efficiency, we are careful about what DB queries we do and what is
    # done in Python. Some logic from CRBApplication.get_for_camp duplicated here

    graph_start_date = camp.start_date - timedelta(365)
    graph_end_date = min(camp.start_date, date.today())

    invited_officers = list(camp.invitations.all()
                            .order_by('date_added')
                            .values_list('officer_id', 'date_added'))
    application_forms = list(applications_for_camp(camp)
                             .order_by('date_submitted')
                             .values_list('id', 'date_submitted'))

    officer_ids = [o[0] for o in invited_officers]
    officer_dates = [o[1] for o in invited_officers]
    app_ids = [a[0] for a in application_forms]
    app_dates = [a[1] for a in application_forms]
    ref_dates = list(ReferenceForm.objects
                     .filter(
                         reference_info__application__in=app_ids,
                         date_created__lte=camp.start_date)
                     .order_by('date_created')
                     .values_list('date_created', flat=True))
    all_crb_info = list(CRBApplication.objects.filter(officer__in=officer_ids,
                                                      completed__lte=camp.start_date
                                                      ).order_by('completed').values_list('completed', 'officer_id'))
    # There can be multiple CRBs for each officer. For 'all CRBs' and 'valid
    # CRBs', we only care about the first.
    all_crb_dates = get_first(all_crb_info)
    valid_crb_dates = get_first([(d, o) for (d, o) in all_crb_info
                                 if d >= camp.start_date - timedelta(days=settings.CRB_VALID_FOR)])

    dr = pd.date_range(start=graph_start_date,
                       end=graph_end_date)

    def trim(ds):
        # this is needed for officer list dates, as officers can sometimes
        # be retrospectively add to officer lists. Also for CRB
        # dates which can be before the year it makes the fillna logic
        # simpler.
        return [max(min(d, graph_end_date), graph_start_date) for d in ds]

    df = pd.DataFrame(
        index=dr,
        data={
            'officer_list_data': accumulate(trim(officer_dates)),
            'application_dates_data': accumulate(app_dates),
            'ref_dates_data': accumulate(ref_dates),
            'all_crb_dates_data': accumulate(trim(all_crb_dates)),
            'valid_crb_dates_data': accumulate(trim(valid_crb_dates)),
        }
        # Fill forward so that accumulated
        # values get propagated to all rows,
        # and then backwards with zeros.
    ).fillna(method='ffill').fillna(value=0)
    return df


def get_first(date_officer_list):
    """
    Given a list of (date, officer id) pairs,
    where there may be duplicate officer ids,
    returns a sorted list of dates, using the first
    date for each officer.
    """
    d = {}
    for completed, off_id in sorted(date_officer_list):
        if off_id not in d:
            d[off_id] = completed
    return sorted(d.values())


def accumulate(date_list):
    return pd.DatetimeIndex(date_list).value_counts().sort_index().cumsum()
