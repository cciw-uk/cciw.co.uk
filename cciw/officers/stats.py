from datetime import date, timedelta

import pandas as pd
from django.conf import settings

from cciw.cciwmain.models import Camp
from cciw.officers.applications import applications_for_camp
from cciw.officers.models import DBSCheck, Reference
from cciw.utils.stats import accumulate_dates


def get_camp_officer_stats(camp: Camp) -> pd.DataFrame:
    # For efficiency, we are careful about what DB queries we do and what is
    # done in Python. Some logic from DBSCheck.get_for_camp duplicated here

    graph_start_date = camp.start_date - timedelta(365)
    graph_end_date = min(camp.start_date, date.today())

    invited_officers = list(camp.invitations.all().order_by("added_on").values_list("officer_id", "added_on"))
    application_forms = list(applications_for_camp(camp).order_by("saved_on").values_list("id", "saved_on"))

    officer_ids = [o[0] for o in invited_officers]
    officer_dates = [o[1] for o in invited_officers]
    app_ids = [a[0] for a in application_forms]
    app_dates = [a[1] for a in application_forms]
    ref_dates = list(
        Reference.objects.filter(referee__application__in=app_ids, created_on__lte=camp.start_date)
        .order_by("created_on")
        .values_list("created_on", flat=True)
    )
    all_dbs_info = list(
        DBSCheck.objects.filter(officer__in=officer_ids, completed_on__lte=camp.start_date)
        .order_by("completed_on")
        .values_list("completed_on", "officer_id")
    )
    # There can be multiple DBSs for each officer. For 'all DBSs' and 'valid
    # DBSs', we only care about the first.
    any_dbs_dates = get_first(all_dbs_info)
    recent_dbs_dates = get_first(
        [(d, o) for (d, o) in all_dbs_info if d >= camp.start_date - timedelta(days=settings.DBS_VALID_FOR)]
    )

    dr = pd.date_range(start=graph_start_date, end=graph_end_date)

    def trim(ds):
        # this is needed for officer list dates, as officers can sometimes
        # be retrospectively add to officer lists. Also for DBS
        # dates which can be before the year it makes the fillna logic
        # simpler.
        return [max(min(d, graph_end_date), graph_start_date) for d in ds]

    df = (
        pd.DataFrame(
            index=dr,
            data={
                "Officers": accumulate_dates(trim(officer_dates)),
                "Applications": accumulate_dates(app_dates),
                "References": accumulate_dates(ref_dates),
                "Any DBS": accumulate_dates(trim(any_dbs_dates)),
                "Recent DBS": accumulate_dates(trim(recent_dbs_dates)),
            },
            # Fill forward so that accumulated
            # values get propagated to all rows,
            # and then backwards with zeros.
        )
        .ffill()
        .fillna(value=0)
    )

    # In order to show the future values correctly (as nothing), we build up a
    # second DataFrame which a larger Index if necessary.
    if camp.start_date > graph_end_date:
        dr2 = pd.date_range(start=graph_start_date, end=camp.start_date)
        df = pd.DataFrame(index=dr2, data=df)
    return df


def get_camp_officer_stats_trend(start_year: int, end_year: int) -> pd.DataFrame:
    years = list(range(start_year, end_year + 1))
    officer_counts = []
    application_counts = []
    reference_in_time_counts = []
    dbs_in_time_counts = []
    for year in years:
        camps = Camp.objects.filter(year=year)
        # It's hard to make use of SQL efficiently here, because the
        # applications_for_camp logic and the DBS application logic can't be
        # captured in SQL efficiently, due to there being no direct link to
        # camps.
        officer_count = 0
        application_count = 0
        reference_in_time_count = 0
        dbs_in_time_count = 0

        # There are some slight 'bugs' here when officers go on mutliple camps.
        # Correct behaviour is tricky to define - for example, if an officer
        # goes on two camps, and for one of them has a valid DBS and the other
        # he/she doesn't, due to dates.
        for camp in camps:
            officer_ids = list(camp.invitations.values_list("officer_id", flat=True))
            officer_count += len(officer_ids)
            application_form_ids = list(applications_for_camp(camp).values_list("id", flat=True))
            application_count += len(application_form_ids)
            reference_in_time_count += Reference.objects.filter(
                referee__application__in=application_form_ids, created_on__lte=camp.start_date
            ).count()
            dbs_in_time_count += DBSCheck.objects.filter(
                officer__in=officer_ids,
                completed_on__isnull=False,
                completed_on__lte=camp.start_date,
                completed_on__gte=camp.start_date - timedelta(days=settings.DBS_VALID_FOR),
            ).count()  # ignores the possibility that an officer can have more than one
        officer_counts.append(officer_count)
        application_counts.append(application_count)
        reference_in_time_counts.append(reference_in_time_count)
        dbs_in_time_counts.append(dbs_in_time_count)
    df = pd.DataFrame(
        index=years,
        data={
            "Officer count": officer_counts,
            "Application count": application_counts,
            "References received in time": reference_in_time_counts,
            "Valid DBS received in time": dbs_in_time_counts,
        },
    )
    df["Application fraction"] = df["Application count"] / df["Officer count"]
    df["References fraction"] = df["References received in time"] / (df["Officer count"] * 2)
    df["Valid DBS fraction"] = df["Valid DBS received in time"] / df["Officer count"]

    return df


def get_first(date_officer_list: list[tuple[date, int]]) -> list[date]:
    """
    Given a list of (date, officer id) pairs,
    where there may be duplicate officer ids,
    returns a sorted list of dates, using the first
    date for each officer.
    """
    d: dict[int, date] = {}
    for completed_on, off_id in sorted(date_officer_list):
        if off_id not in d:
            d[off_id] = completed_on
    return sorted(d.values())
