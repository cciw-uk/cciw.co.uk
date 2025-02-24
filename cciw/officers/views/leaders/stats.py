import pandas as pd
import pandas_highcharts.core
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from cciw.bookings.stats import get_booking_ages_stats, get_booking_progress_stats
from cciw.cciwmain.common import CampId
from cciw.cciwmain.models import Camp
from cciw.utils.spreadsheet import ExcelFromDataFrameBuilder

from ...stats import get_camp_officer_stats, get_camp_officer_stats_trend
from ..utils.auth import (
    camp_admin_required,
)
from ..utils.breadcrumbs import leaders_breadcrumbs, officers_breadcrumbs, with_breadcrumbs
from ..utils.campid import get_camp_or_404
from ..utils.spreadsheets import spreadsheet_response


@staff_member_required
@camp_admin_required
@with_breadcrumbs(leaders_breadcrumbs)
def officer_stats(request, year: int):
    camps = list(Camp.objects.filter(year=year).order_by("camp_name__slug"))
    if len(camps) == 0:
        raise Http404

    charts = []
    for camp in camps:
        df = get_camp_officer_stats(camp)
        df["References ÷ 2"] = df["References"] / 2  # Make it match the height of others
        df.pop("References")
        charts.append(
            (
                camp,
                pandas_highcharts.core.serialize(
                    df, title=f"{camp.name} - {camp.leaders_formatted}", output_type="json"
                ),
            )
        )
    return TemplateResponse(
        request,
        "cciw/officers/stats.html",
        {
            "camps": camps,
            "title": f"Officer stats {year}",
            "year": year,
            "charts": charts,
        },
    )


@staff_member_required
@camp_admin_required
@with_breadcrumbs(leaders_breadcrumbs)
def officer_stats_trend(request, start_year: int, end_year: int):
    start_year = int(start_year)
    end_year = int(end_year)
    data = get_camp_officer_stats_trend(start_year, end_year)
    for c in data.columns:
        if "fraction" not in c:
            data.pop(c)
    fraction_to_percent(data)
    return TemplateResponse(
        request,
        "cciw/officers/stats_trend.html",
        {
            "title": f"Officer stats {start_year}-{end_year}",
            "start_year": start_year,
            "end_year": end_year,
            "chart_data": pandas_highcharts.core.serialize(
                data, title=f"Officer stats {start_year} - {end_year}", output_type="json"
            ),
        },
    )


@staff_member_required
@camp_admin_required
def officer_stats_download(request, year: int) -> HttpResponse:
    camps = list(Camp.objects.filter(year=year).order_by("camp_name__slug"))
    builder = ExcelFromDataFrameBuilder()
    for camp in camps:
        builder.add_sheet_from_dataframe(str(camp.url_id), get_camp_officer_stats(camp))
    return spreadsheet_response(
        builder,
        f"CCIW-officer-stats-{year}",
        notice=None,
    )


@staff_member_required
@camp_admin_required
def officer_stats_trend_download(request, start_year: int, end_year: int) -> HttpResponse:
    builder = ExcelFromDataFrameBuilder()
    builder.add_sheet_from_dataframe("Officer stats trend", get_camp_officer_stats_trend(start_year, end_year))
    return spreadsheet_response(builder, f"CCIW-officer-stats-trend-{start_year}-{end_year}", notice=None)


def fraction_to_percent(data):
    for col_name in list(data.columns):
        parts = col_name.split(" ")
        new_name = " ".join("%" if p.lower() == "fraction" else p for p in parts)
        if new_name != col_name:
            data[new_name] = data[col_name] * 100
            data.pop(col_name)


def _get_booking_progress_stats_from_params(start_year, end_year, camp_ids, **kwargs):
    start_year, end_year, camps = _parse_year_or_camp_ids(start_year, end_year, camp_ids)
    if camps is not None:
        data_dates, data_rel_days = get_booking_progress_stats(camps=camps, **kwargs)
    else:
        data_dates, data_rel_days = get_booking_progress_stats(start_year=start_year, end_year=end_year, **kwargs)

    return start_year, end_year, camps, data_dates, data_rel_days


@staff_member_required
@camp_admin_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_progress_stats(
    request, start_year: int | None = None, end_year: int | None = None, camp_ids: list[CampId] | None = None
):
    start_year, end_year, camp_objs, data_dates, data_rel_days = _get_booking_progress_stats_from_params(
        start_year, end_year, camp_ids, overlay_years=True
    )
    return TemplateResponse(
        request,
        "cciw/officers/booking_progress_stats.html",
        {
            "title": "Booking progress" + (f" {start_year}-{end_year}" if start_year else ""),
            "start_year": start_year,
            "end_year": end_year,
            "camps": camp_objs,
            "camp_ids": camp_ids,
            "dates_chart_data": pandas_highcharts.core.serialize(
                data_dates, title="Bookings by date", output_type="json"
            ),
            "rel_days_chart_data": pandas_highcharts.core.serialize(
                data_rel_days,
                title="Bookings by days relative to start of camp",
                output_type="json",
            ),
        },
    )


@staff_member_required
@camp_admin_required
def booking_progress_stats_download(
    request, start_year: int | None = None, end_year: int | None = None, camp_ids: list[CampId] | None = None
):
    start_year, end_year, camp_objs, data_dates, data_rel_days = _get_booking_progress_stats_from_params(
        start_year, end_year, camp_ids, overlay_years=False
    )
    builder = ExcelFromDataFrameBuilder()
    builder.add_sheet_from_dataframe("Bookings against date", data_dates)
    builder.add_sheet_from_dataframe("Days relative to start of camp", data_rel_days)
    if camp_ids is not None:
        filename = f"CCIW-booking-progress-stats-{'_'.join(str(camp_id) for camp_id in camp_ids)}"
    else:
        filename = f"CCIW-booking-progress-stats-{start_year}-{end_year}"
    return spreadsheet_response(
        builder,
        filename,
        notice=None,
    )


@staff_member_required
@camp_admin_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_ages_stats(
    request,
    start_year: int | None = None,
    end_year: int | None = None,
    camp_ids: list[CampId] | None = None,
    single_year: int | None = None,
):
    if single_year is not None:
        camps = Camp.objects.filter(year=int(single_year))
        return HttpResponseRedirect(
            reverse("cciw-officers-booking_ages_stats_custom", kwargs={"camp_ids": [c.url_id for c in camps]})
        )
    start_year, end_year, camps, data = _get_booking_ages_stats_from_params(start_year, end_year, camp_ids)
    if "Total" in data:
        data.pop("Total")

    if camps:
        if all(c.year == camps[0].year for c in camps):
            stack_columns = True
        else:
            stack_columns = False
    else:
        stack_columns = False

    # Use colors defined for camps if possible. To get them to line up with data
    # series, we have to sort in the same way the pandas_highcharts does i.e. by
    # series name
    colors = []
    if camps:
        colors = [color for (title, color) in sorted((str(c.url_id), c.camp_name.color) for c in camps)]
        if len(set(colors)) != len(colors):
            # Not enough - fall back to auto
            colors = []

    return TemplateResponse(
        request,
        "cciw/officers/booking_ages_stats.html",
        {
            "title": "Camper ages stats" + (f" {start_year}-{end_year}" if start_year else ""),
            "start_year": start_year,
            "end_year": end_year,
            "camps": camps,
            "camp_ids": camp_ids,
            "chart_data": pandas_highcharts.core.serialize(data, title="Age of campers", output_type="json"),
            "colors_data": colors,
            "stack_columns": stack_columns,
        },
    )


@staff_member_required
@camp_admin_required
def booking_ages_stats_download(
    request, start_year: int | None = None, end_year: int | None = None, camp_ids: list[CampId] | None = None
):
    start_year, end_year, camps, data = _get_booking_ages_stats_from_params(start_year, end_year, camp_ids)
    builder = ExcelFromDataFrameBuilder()
    builder.add_sheet_from_dataframe("Age of campers", data)
    if camp_ids is not None:
        filename = f"CCIW-booking-ages-stats-{'_'.join(str(camp_id) for camp_id in camp_ids)}"
    else:
        filename = f"CCIW-booking-ages-stats-{start_year}-{end_year}"
    return spreadsheet_response(builder, filename, notice=None)


def _get_booking_ages_stats_from_params(
    start_year: int | None, end_year: int | None, camp_ids: list[CampId] | None
) -> tuple[int | None, int | None, list[Camp] | None, pd.DataFrame]:
    start_year, end_year, camps = _parse_year_or_camp_ids(start_year, end_year, camp_ids)
    if camps is not None:
        data = get_booking_ages_stats(camps=camps, include_total=True)
    else:
        data = get_booking_ages_stats(start_year=start_year, end_year=end_year, include_total=False)
    return start_year, end_year, camps, data


def _parse_year_or_camp_ids(start_year, end_year, camp_ids):
    if camp_ids is not None:
        return None, None, [get_camp_or_404(camp_id) for camp_id in camp_ids]
    else:
        return int(start_year), int(end_year), None
