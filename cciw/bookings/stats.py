from datetime import timedelta

import datedelta
import pandas as pd
from django.db import models

from cciw.utils.stats import accumulate, accumulate_dates, counts

from .models import Booking


def get_booking_progress_stats(start_year=None, end_year=None, camps=None, overlay_years=False):
    data_dates = {}
    data_rel_days = {}
    if camps:
        items = camps
        query_filter = lambda qs, camp: qs.filter(camp=camp)
        labeller = lambda camp: str(camp.url_id)
        last_year = max([c.year for c in camps])
    else:
        items = range(start_year, end_year + 1)
        query_filter = lambda qs, year: qs.filter(camp__year=year)
        labeller = str
        last_year = end_year

    for item in items:
        qs = Booking.objects.confirmed()
        rows = query_filter(qs, item).select_related('camp').values_list('booked_at', 'created', 'camp__start_date')
        rows2 = [[r[0] if r[0] else r[1], r[2]] for r in rows]  # prefer 'booked_at' to 'created'
        if rows2:
            if overlay_years:
                dates = [d1.date() + datedelta.datedelta(years=last_year - d2.year) for d1, d2 in rows2]
            else:
                dates = [d1.date() for d1, d2 in rows2]
            label = labeller(item)
            data_dates[label] = _fill_gaps(accumulate_dates(dates))
            data_rel_days[label] = _fill_gaps(accumulate([(r[0].date() - r[1]).days for r in rows2]))

    df1 = pd.DataFrame(data=data_dates)
    df2 = pd.DataFrame(data=data_rel_days)
    return df1, df2


def _fill_gaps(series):
    # pandas 'fillna' method not good enough for us - we want the current year
    # not to be filled until the end of the chart, just missing in-between values
    # to be filled.
    last_idx = None
    last_val = None
    extra = []
    for idx in series.index:
        if last_idx is not None:
            if isinstance(idx, pd.Timestamp):
                current_dt = idx.date()
                last_dt = last_idx.date()
                missing_dates = [last_dt + timedelta(days=days)
                                 for days in range(1, (current_dt - last_dt).days)]
                extra.extend((pd.Timestamp(dt), last_val) for dt in missing_dates)
            else:
                missing_days = [last_idx + days
                                for days in range(1, idx - last_idx)]
                extra.extend((day, last_val) for day in missing_days)

        last_idx = idx
        last_val = series[idx]

    for idx, val in extra:
        series[idx] = val
    series = series.sort_index()
    return series


def get_booking_summary_stats(start_year, end_year):
    rows = (Booking.objects.confirmed().select_related('camp')
            .filter(camp__year__gte=start_year, camp__year__lte=end_year)
            .values_list('camp__year', 'sex')
            .order_by('camp__year', 'sex')
            .annotate(count=models.Count('sex')))
    data = {s1: [c for y, s, c in rows
                 if s == s1[0].lower()]
            for s1 in ['Male', 'Female']}
    years = sorted(list(set(y for y, s, c in rows)))
    df = pd.DataFrame(index=years,
                      data=data)
    df['Total'] = df['Male'] + df['Female']
    return df


def get_booking_ages_stats(start_year=None, end_year=None, camps=None, include_total=True):
    if camps:
        items = camps
        query_filter = lambda qs, camp: qs.filter(camp=camp)
        labeller = lambda camp: str(camp.url_id)
    else:
        items = range(start_year, end_year + 1)
        query_filter = lambda qs, year: qs.filter(camp__year=year)
        labeller = str

    data = {}
    for item in items:
        qs = (Booking.objects.confirmed()
              .select_related(None).select_related('camp')
              .only('date_of_birth', 'camp'))
        objs = query_filter(qs, item)
        vals = [b.age_on_camp() for b in objs]
        data[labeller(item)] = counts(vals)
    df = pd.DataFrame(data=data).fillna(0)
    if include_total:
        df['Total'] = sum(df[col] for col in data)
    return df
