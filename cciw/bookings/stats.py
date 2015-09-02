import pandas as pd
from django.db import connection

from cciw.utils.stats import accumulate, accumulate_dates

from .models import Booking


def get_booking_progress_stats(start_year, end_year, overlay_years=False):
    data_dates = {}
    data_rel_days = {}
    for year in range(start_year, end_year + 1):
        rows = Booking.objects.booked().filter(camp__year=year).select_related('camp').values_list('booked_at', 'created', 'camp__start_date')
        rows2 = [[r[0] if r[0] else r[1], r[2]] for r in rows]  # prefer 'booked_at' to 'created'
        if rows2:
            if overlay_years:
                dates = [d1.date().replace(year=d1.date().year - d2.year + end_year) for d1, d2 in rows2]
            else:
                dates = [d1.date() for d1, d2 in rows2]
            data_dates[str(year)] = accumulate_dates(dates)
            data_rel_days[str(year)] = accumulate([(r[0].date() - r[1]).days for r in rows2])

    df1 = pd.DataFrame(data=data_dates).fillna(method='ffill').fillna(0)
    df2 = pd.DataFrame(data=data_rel_days).fillna(method='ffill').fillna(0)
    return df1, df2


def get_booking_summary_stats(start_year, end_year):
    c = connection.cursor()
    c.execute("""
    SELECT year, sex, count(sex)
    FROM bookings_booking AS booking
       INNER JOIN cciwmain_camp AS camp
       ON booking.camp_id = camp.id
    WHERE camp.year >= %s AND camp.year <= %s
    GROUP BY camp.year, booking.sex
    ORDER BY year, sex;
    """, [start_year, end_year])
    rows = c.fetchall()
    data = {s1: [c for y, s, c in rows
                 if s == s1[0].lower()]
            for s1 in ['Male', 'Female']}
    years = sorted(list(set(y for y, s, c in rows)))
    df = pd.DataFrame(index=years,
                      data=data)
    df['Total'] = df['Male'] + df['Female']
    return df
