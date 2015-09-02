from datetime import timedelta
import pandas as pd

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
