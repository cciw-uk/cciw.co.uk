from datetime import date, timedelta

import pandas as pd
from django.conf import settings

from cciw.cciwmain.models import Camp
from cciw.officers.applications import applications_for_camp
from cciw.officers.models import ReferenceForm, CRBApplication
from cciw.utils.stats import accumulate_dates


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
                     .filter(reference_info__application__in=app_ids,
                             date_created__lte=camp.start_date)
                     .order_by('date_created')
                     .values_list('date_created', flat=True))
    all_crb_info = list(CRBApplication.objects
                        .filter(officer__in=officer_ids,
                                completed__lte=camp.start_date)
                        .order_by('completed')
                        .values_list('completed', 'officer_id'))
    # There can be multiple CRBs for each officer. For 'all CRBs' and 'valid
    # CRBs', we only care about the first.
    any_crb_dates = get_first(all_crb_info)
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
            'Officers': accumulate_dates(trim(officer_dates)),
            'Applications': accumulate_dates(app_dates),
            'References': accumulate_dates(ref_dates),
            'Any DBS': accumulate_dates(trim(any_crb_dates)),
            'Valid DBS': accumulate_dates(trim(valid_crb_dates)),
        }
        # Fill forward so that accumulated
        # values get propagated to all rows,
        # and then backwards with zeros.
    ).fillna(method='ffill').fillna(value=0)
    return df


def get_camp_officer_stats_trend(start_year, end_year):
    years = list(range(start_year, end_year + 1))
    officer_counts = []
    application_counts = []
    reference_in_time_counts = []
    crb_in_time_counts = []
    for year in years:
        camps = Camp.objects.filter(year=year)
        # It's hard to make use of SQL efficiently here, because the
        # applications_for_camp logic and the CRB application logic can't be
        # captured in SQL efficiently, due to there being no direct link to
        # camps.
        officer_count = 0
        application_count = 0
        reference_in_time_count = 0
        crb_in_time_count = 0

        # There are some slight 'bugs' here when officers go on mutliple camps.
        # Correct behaviour is tricky to define - for example, if an officer
        # goes on two camps, and for one of them has a valid CRB and the other
        # he/she doesn't, due to dates.
        for camp in camps:
            officer_ids = list(camp.invitations.values_list('officer_id', flat=True))
            officer_count += len(officer_ids)
            application_form_ids = list(applications_for_camp(camp).values_list('id', flat=True))
            application_count += len(application_form_ids)
            reference_in_time_count += ReferenceForm.objects.filter(
                reference_info__application__in=application_form_ids,
                date_created__lte=camp.start_date
            ).count()
            crb_in_time_count += CRBApplication.objects.filter(
                officer__in=officer_ids,
                completed__isnull=False,
                completed__lte=camp.start_date,
                completed__gte=camp.start_date - timedelta(days=settings.CRB_VALID_FOR)
            ).count()  # ignores the possibility that an officer can have more than one
        officer_counts.append(officer_count)
        application_counts.append(application_count)
        reference_in_time_counts.append(reference_in_time_count)
        crb_in_time_counts.append(crb_in_time_count)
    df = pd.DataFrame(index=years,
                      data={'Officer count': officer_counts,
                            'Application count': application_counts,
                            'References received in time': reference_in_time_counts,
                            'Valid DBS received in time': crb_in_time_counts,
                            })
    df['Application fraction'] = df['Application count'] / df['Officer count']
    df['References fraction'] = df['References received in time'] / (df['Officer count'] * 2)
    df['Valid DBS fraction'] = df['Valid DBS received in time'] / df['Officer count']

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
