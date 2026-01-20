import contextlib
from datetime import datetime

import pandas_highcharts.core
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from cciw.bookings.models import Booking, Price
from cciw.bookings.models.prices import are_prices_set_for_year
from cciw.bookings.models.queue import (
    FIRST_TIMER_PERCENTAGE,
    BookingQueueEntry,
    allocate_places_and_notify,
    get_camp_booking_queue_ranking_result,
)
from cciw.bookings.models.yearconfig import get_year_config
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
from cciw.utils.views import for_htmx2

from .utils.auth import (
    booking_secretary_or_treasurer_required,
    booking_secretary_required,
    camp_admin_required,
    cciw_secretary_or_booking_secretary_required,
    secretary_or_committee_required,
)
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs
from .utils.data_retention import DataRetentionNotice, show_data_retention_notice
from .utils.spreadsheets import spreadsheet_response

EXPORT_PAYMENT_DATE_FORMAT = "%Y-%m-%d"

BOOKING_STATS_PREVIOUS_YEARS = 4


@staff_member_required
@booking_secretary_required
@show_data_retention_notice(DataRetentionNotice.CAMPERS, "Camper data")
def export_camper_data_for_year(request, year: int):
    return spreadsheet_response(
        year_bookings_to_spreadsheet(year),
        f"CCIW-bookings-{year}",
        notice=DataRetentionNotice.CAMPERS,
    )


# treasurer gets to see these to know how much money
# to transfer to camp leaders.
@booking_secretary_or_treasurer_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_secretary_reports(request, year: int):
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
def export_payment_data(request):
    date_start = request.GET["start"]
    date_end = request.GET["end"]
    date_start = datetime.strptime(date_start, EXPORT_PAYMENT_DATE_FORMAT).replace(
        tzinfo=timezone.get_default_timezone()
    )
    date_end = datetime.strptime(date_end, EXPORT_PAYMENT_DATE_FORMAT).replace(tzinfo=timezone.get_default_timezone())
    return spreadsheet_response(
        payments_to_spreadsheet(date_start, date_end),
        f"CCIW-payments-{date_start:%Y-%m-%d}-to-{date_end:%Y-%m-%d}",
        notice=DataRetentionNotice.CAMPERS,
    )


@staff_member_required
@secretary_or_committee_required
@with_breadcrumbs(officers_breadcrumbs)
def booking_summary_stats(request, start_year: int, end_year: int):
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


@staff_member_required
@secretary_or_committee_required
def booking_summary_stats_download(request, start_year: int, end_year: int):
    data = get_booking_summary_stats(start_year, end_year)
    builder = ExcelFromDataFrameBuilder()
    builder.add_sheet_from_dataframe("Bookings", data)
    return spreadsheet_response(builder, f"CCIW-booking-summary-stats-{start_year}-{end_year}", notice=None)


@booking_secretary_required
@json_response
def place_availability_json(request):
    retval: dict[str, object] = {"status": "success"}
    camp_id = int(request.GET["camp_id"])
    camp: Camp = Camp.objects.get(id=camp_id)
    places = camp.get_places_left()
    retval["result"] = dict(total=places.total, male=places.male, female=places.female)
    return retval


@booking_secretary_required
@json_response
def booking_problems_json(request):
    """
    Get the booking problems associated with the data POSTed.
    """
    # This is used by the admin.
    # We have to create a Booking object, but not save it.
    from cciw.bookings.admin import BookingAdminForm

    # Make it easy on front end:
    data = request.POST.copy()
    with contextlib.suppress(KeyError):
        data["created_at"] = data["created_at_0"] + " " + data["created_at_1"]

    if "booking_id" in data:
        booking_obj = Booking.objects.get(id=int(data["booking_id"]))
        if "created_online" not in data:
            # readonly field, data not included in form
            data["created_online"] = booking_obj.created_online
        form = BookingAdminForm(data, instance=booking_obj)
    else:
        form = BookingAdminForm(data)

    retval: dict[str, object] = {"status": "success"}
    if form.is_valid():
        retval["valid"] = True
        instance: Booking = form.save(commit=False)
        # We will get errors later on if prices don't exist for the year chosen, so
        # we check that first.
        if not are_prices_set_for_year(instance.camp.year):
            retval["problems"] = [f"Prices have not been set for the year {instance.camp.year}"]
        else:
            problems = instance.get_booking_problems(booking_sec=True)
            retval["problems"] = [p.description for p in problems]
    else:
        retval["valid"] = False
        retval["errors"] = form.errors
    return retval


@json_response
@staff_member_required
@booking_secretary_required
def get_booking_expected_amount_due(request):
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
def brochure_mailing_list(request, year: int):
    return spreadsheet_response(
        addresses_for_mailing_list(year), f"CCIW-mailing-list-{year}", notice=DataRetentionNotice.CAMPERS
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
@for_htmx2(use_partial_from_params=True)
def booking_queue(request: HttpRequest, camp_id: CampId) -> HttpResponse:
    camp = get_camp_or_404(camp_id)
    year_config = get_year_config(year=camp.year)
    if year_config is None:
        raise Http404(
            f"The booking queue for {camp.nice_name} can't be accessed until the booking configuration dates for {camp.year} have been defined"
        )

    ranking_result = get_camp_booking_queue_ranking_result(camp=camp, year_config=year_config)

    # TODO - check dates in year_config before enabling this button

    can_allocate_places = request.user.is_booking_secretary
    if can_allocate_places and request.method == "POST" and "allocate" in request.POST:
        result = allocate_places_and_notify(ranking_result.bookings, by_user=request.user)
        messages.info(
            request,
            f"{result.accepted_account_count} places have been allocated, "
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
        "can_edit_bookings": request.user.can_edit_bookings,
        "can_allocate_places": can_allocate_places,
    }
    return TemplateResponse(request, "cciw/officers/booking_queue.html", context)


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
            "can_edit_bookings": request.user.can_edit_bookings,
        },
        headers=headers,
    )
