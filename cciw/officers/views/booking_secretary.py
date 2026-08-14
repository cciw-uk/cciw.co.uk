from datetime import datetime

import pandas_highcharts.core
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from cciw.bookings.models import Booking, Price
from cciw.bookings.models.queue import (
    FIRST_TIMER_PERCENTAGE,
    BookingQueueEntry,
    allocate_places_and_notify,
    get_camp_booking_queue_ranking_result,
)
from cciw.bookings.models.yearconfig import get_booking_open_data, get_year_config
from cciw.bookings.stats import get_booking_summary_stats
from cciw.bookings.utils import (
    addresses_for_mailing_list,
    payments_to_spreadsheet,
    year_bookings_to_spreadsheet,
)
from cciw.cciwmain.common import CampId
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp
from cciw.officers.forms import UpdateQueueEntryForm
from cciw.officers.views.utils.campid import get_camp_or_404
from cciw.utils.spreadsheet import ExcelFromDataFrameBuilder
from cciw.utils.views import for_htmx

from ..models.data_retention import (
    DataRelatedToCampersYear,
    NoSensitiveData,
)
from .utils.auth import (
    booking_secretary_or_treasurer_required,
    booking_secretary_required,
    camp_admin_required,
    cciw_secretary_or_booking_secretary_required,
    secretary_or_committee_required,
)
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs
from .utils.data_retention import (
    DataRetentionRule,
    SensitiveDownloadResponse,
    sensitive_data_download,
)
from .utils.spreadsheets import spreadsheet_response

EXPORT_PAYMENT_DATE_FORMAT = "%Y-%m-%d"

BOOKING_STATS_PREVIOUS_YEARS = 4


def bookings_data_filename_stem(year: int) -> str:
    return f"CCIW-bookings-{year}"


@booking_secretary_required
@sensitive_data_download(skip_notice=True)
def export_camper_data_for_year(request: HttpRequest, year: int) -> SensitiveDownloadResponse:
    return spreadsheet_response(
        year_bookings_to_spreadsheet(year),
        bookings_data_filename_stem(year),
        rule=DataRetentionRule.CAMPERS,
        data_relation=DataRelatedToCampersYear(year=year),
    )


# treasurer gets to see these to know how much money
# to transfer to camp leaders.
@booking_secretary_or_treasurer_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_secretary_reports(request: HttpRequest, year: int):
    from cciw.bookings.models import Booking, booking_report_by_camp, outstanding_bookings_with_fees

    # 1. Camps and their booking levels.
    camps = booking_report_by_camp(year)

    # 2. Online bookings needing attention
    to_approve = Booking.objects.need_approving().for_year(year)

    # 3. Fees
    outstanding = outstanding_bookings_with_fees(year)

    export_start = datetime(year - 1, 11, 1)  # November previous year
    export_end = datetime(year, 10, 31)  # November this year
    export_data_link = (
        reverse("cciw-officers-export_payment_data")
        + f"?start={export_start.strftime(EXPORT_PAYMENT_DATE_FORMAT)}&end={export_end.strftime(EXPORT_PAYMENT_DATE_FORMAT)}"
    )

    return TemplateResponse(
        request,
        "cciw/officers/booking_secretary_reports.html",
        {
            "title": f"Bookings {year}",
            "year": year,
            "stats_start_year": year - BOOKING_STATS_PREVIOUS_YEARS,
            "camps": camps,
            "bookings": outstanding,
            "to_approve": to_approve,
            "export_start": export_start,
            "export_end": export_end,
            "export_data_link": export_data_link,
        },
    )


@booking_secretary_required
@sensitive_data_download(skip_notice=True)
def export_payment_data(request: HttpRequest) -> SensitiveDownloadResponse:
    date_start = request.GET["start"]
    date_end = request.GET["end"]
    date_start = datetime.strptime(date_start, EXPORT_PAYMENT_DATE_FORMAT).replace(
        tzinfo=timezone.get_default_timezone()
    )
    date_end = datetime.strptime(date_end, EXPORT_PAYMENT_DATE_FORMAT).replace(tzinfo=timezone.get_default_timezone())
    return spreadsheet_response(
        payments_to_spreadsheet(date_start, date_end),
        f"CCIW-payments-{date_start:%Y-%m-%d}-to-{date_end:%Y-%m-%d}",
        rule=DataRetentionRule.CAMPERS,
        # We base data relation on the last year that might be included.
        data_relation=DataRelatedToCampersYear(year=date_end.year),
    )


@secretary_or_committee_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_summary_stats(request: HttpRequest, start_year: int, end_year: int) -> HttpResponse:
    chart_data = get_booking_summary_stats(start_year, end_year)
    chart_data.pop("Total")
    return TemplateResponse(
        request,
        "cciw/officers/booking_summary_stats.html",
        {
            "title": f"Booking summary {start_year}-{end_year}",
            "start_year": start_year,
            "end_year": end_year,
            "chart_data": pandas_highcharts.core.serialize(chart_data, output_type="json"),
        },
    )


@secretary_or_committee_required
def booking_summary_stats_download(request: HttpRequest, start_year: int, end_year: int) -> HttpResponse:
    data = get_booking_summary_stats(start_year, end_year)
    builder = ExcelFromDataFrameBuilder()
    builder.add_sheet_from_dataframe("Bookings", data)
    return spreadsheet_response(
        builder,
        f"CCIW-booking-summary-stats-{start_year}-{end_year}",
        rule=None,
        data_relation=NoSensitiveData(),
    )


@booking_secretary_required
@json_response
def place_availability_json(request: HttpRequest) -> dict:
    retval: dict[str, object] = {"status": "success"}
    camp_id = int(request.GET["camp_id"])
    camp: Camp = Camp.objects.get(id=camp_id)
    places = camp.get_places_left()
    retval["result"] = dict(total=places.total, male=places.male, female=places.female)
    return retval


@booking_secretary_required
@json_response
def get_booking_expected_amount_due(request: HttpRequest) -> dict:
    fail = {"status": "success", "amount": None}
    try:
        # If we use a form to construct an object, we won't get pass
        # validation. So we construct a partial object, doing manual parsing of
        # posted vars.

        if "id" in request.POST:
            # Start with saved data if it is available
            b = Booking.objects.get(id=int(request.POST["id"]))
        else:
            b = Booking()
        b.price_type = int(request.POST["price_type"])
        b.camp_id = int(request.POST["camp"])
        b.state = int(request.POST["state"])
    except (ValueError, KeyError):  # not a valid price_type/camp, data missing
        return fail
    try:
        amount = b.expected_amount_due()
    except Price.DoesNotExist:
        return fail

    if amount is not None:
        amount = str(amount)  # convert decimal
    return {"status": "success", "amount": amount}


@cciw_secretary_or_booking_secretary_required
@sensitive_data_download(skip_notice=True)
def brochure_mailing_list(request: HttpRequest, year: int) -> SensitiveDownloadResponse:
    return spreadsheet_response(
        addresses_for_mailing_list(year),
        f"CCIW-mailing-list-{year}",
        rule=DataRetentionRule.CAMPERS,
        data_relation=DataRelatedToCampersYear(year=year),
    )


@camp_admin_required
def booking_queues(request: HttpRequest, year: int) -> HttpResponse:
    camps = Camp.objects.filter(year=int(year))
    context = {
        "camps": camps,
        "title": "Booking queues",
    }
    return TemplateResponse(request, "cciw/officers/booking_queues.html", context)


@camp_admin_required
@for_htmx(use_partial_from_params=True)
def booking_queue(request: HttpRequest, camp_id: CampId) -> HttpResponse:
    camp = get_camp_or_404(camp_id)
    year_config = get_year_config(year=camp.year)
    if year_config is None:
        raise Http404(
            f"The booking queue for {camp.nice_name} can't be accessed until the booking configuration dates for {camp.year} have been defined"
        )

    ranking_result = get_camp_booking_queue_ranking_result(camp=camp, year_config=year_config)

    booking_open_data = get_booking_open_data(camp.year)
    can_allocate_places = request.user.is_booking_secretary and booking_open_data.is_closed_for_initial_period
    if can_allocate_places and request.method == "POST" and "allocate" in request.POST:
        result = allocate_places_and_notify(ranking_result.bookings, by_user=request.user)
        messages.info(
            request,
            f"{result.accepted_booking_count} places have been allocated, "
            + f"and {result.accepted_account_count} accounts have been emailed.",
        )
        if result.declined_and_notified_account_count:
            messages.info(
                request,
                f"{result.declined_and_notified_account_count} accounts have been notified that places have been declined.",
            )
        return HttpResponseRedirect(".")

    context = {
        "camp": camp,
        "year": camp.year,
        "last_year": camp.year - 1,
        "places_booked": ranking_result.places_booked,
        "places_left": ranking_result.places_left,
        "ready_to_allocate": ranking_result.ready_to_allocate,
        "title": f"Booking queue - {camp.nice_name}",
        "ranked_queue_bookings": ranking_result.bookings,
        "edit_queue_entry_mode": False,
        "problems": ranking_result.problems,
        "FIRST_TIMER_PERCENTAGE": FIRST_TIMER_PERCENTAGE,
        "booking_open_data": booking_open_data,
        "can_allocate_places": can_allocate_places,
    } | _booking_context_common(request)
    return TemplateResponse(request, "cciw/officers/booking_queue.html", context)


def _booking_context_common(request) -> dict:
    can_edit_bookings = request.user.can_edit_bookings
    can_view_booking_info = (can_edit_bookings or request.user.can_view_booking_info,)
    return {
        "can_edit_bookings": can_edit_bookings,
        "can_view_booking_info": can_view_booking_info,
    }


@camp_admin_required
def booking_queue_row(request: HttpRequest, camp_id: CampId) -> HttpResponse:
    assert request.method == "POST"
    assert "Hx-Request" in request.headers
    camp = get_camp_or_404(camp_id)
    year_config = get_year_config(year=camp.year)
    assert year_config is not None
    trigger_page_update = False
    booking_id = int(request.POST["booking_id"])

    # We need all the bookings, ranked, to be able to show one row correctly,
    # due to the 'Allocate' column.
    ranking_result = get_camp_booking_queue_ranking_result(camp=camp, year_config=year_config)
    booking = [b for b in ranking_result.bookings if b.id == booking_id][0]
    queue_entry: BookingQueueEntry = booking.queue_entry

    assert year_config is not None

    if "edit-queue-entry" in request.POST:
        # Show edit form
        form = UpdateQueueEntryForm(instance=queue_entry)
        edit_queue_entry_mode = True

    elif "save-queue-entry" in request.POST:
        # save the data, refresh the whole page.
        old_queue_entry_fields = queue_entry.get_current_field_data()
        form = UpdateQueueEntryForm(data=request.POST, instance=queue_entry)
        if form.is_valid():
            form.save()
            queue_entry.save_fields_changed_action_log(by_user=request.user, old_fields=old_queue_entry_fields)
            edit_queue_entry_mode = False
            trigger_page_update = True
        else:
            edit_queue_entry_mode = True
    else:
        # Cancel button.
        # Do nothing, just re-render the row
        edit_queue_entry_mode = False
        form = None

    headers = {}
    if trigger_page_update:
        headers["HX-Trigger"] = f"refreshBookingQueueForCamp-{camp.id}"

    return TemplateResponse(
        request,
        "cciw/officers/booking_queue_row_inc.html",
        {
            "camp": camp,
            "booking": booking,
            "edit_queue_entry_mode": edit_queue_entry_mode,
            "form": form,
        }
        | _booking_context_common(request),
        headers=headers,
    )
