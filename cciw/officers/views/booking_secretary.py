import contextlib
from datetime import datetime

import pandas_highcharts.core
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from cciw.bookings.models import Booking, Price
from cciw.bookings.models.prices import are_prices_set_for_year
from cciw.bookings.models.queue import add_queue_cutoffs, rank_queue_bookings
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

from .utils.auth import (
    booking_secretary_or_treasurer_required,
    booking_secretary_required,
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
        b.early_bird_discount = "early_bird_discount" in request.POST
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


@cciw_secretary_or_booking_secretary_required
def booking_queues(request: HttpRequest, year: int) -> HttpResponse:
    camps = Camp.objects.filter(year=int(year))
    context = {
        "camps": camps,
        "title": "Booking queues",
    }
    return TemplateResponse(request, "cciw/officers/booking_queues.html", context)


@cciw_secretary_or_booking_secretary_required
def booking_queue(request: HttpRequest, camp_id: CampId) -> HttpResponse:
    camp = get_camp_or_404(camp_id)
    places_left = camp.get_places_left()
    edit_queue_entry_mode = False

    refresh_contents_only = False

    if request.headers.get("Hx-Request", False) and request.method == "POST":
        if "cancel-edit-queue-entry" in request.POST:
            # Do nothing, just refresh the whole list.
            refresh_contents_only = True
        elif "edit-queue-entry" in request.POST or "save-queue-entry" in request.POST:
            # htmx edit row mode.

            # Changing any fields can change the ranking, so we have to update
            # the whole list, so this isn't like the "edit single row"
            # functionality in many pages where we can update just one part of
            # the page.

            # For edit mode, we do want to render just one row, but we need to
            # get the ranking info for the whole camp, so we can show the right
            # data in the other cells.
            booking_id = int(request.POST["booking_id"])
            ranked_queue_bookings = rank_queue_bookings(camp)
            booking = [b for b in ranked_queue_bookings if b.id == booking_id][0]
            queue_entry = booking.queue_entry

            if "edit-queue-entry" in request.POST:
                # Show edit form
                form = UpdateQueueEntryForm(instance=queue_entry)
                edit_queue_entry_mode = True

            elif "save-queue-entry" in request.POST:
                # save the data, refresh the whole page.
                form = UpdateQueueEntryForm(data=request.POST, instance=queue_entry)
                if form.is_valid():
                    form.save()
                    # show whole list.
                    refresh_contents_only = True
                else:
                    edit_queue_entry_mode = True

            if edit_queue_entry_mode:
                # Initial edit mode, or failed 'save'
                return TemplateResponse(
                    request,
                    "cciw/officers/booking_queue_row_inc.html",
                    {
                        "booking": booking,
                        "edit_queue_entry_mode": edit_queue_entry_mode,
                        "form": form,
                    },
                    headers={"HX-Retarget": f"[data-booking-id='{booking.id}']"},
                )

    # TODO - UI for fixing up sibling fuzzy matching, if needed?

    # TODO - show warnings for:
    # - first timer allocations greater than 10%

    # TODO - buttons to confirm places. Take to a different page.
    # TODO - track changes that are made via this page, for auditing

    ranked_queue_bookings = rank_queue_bookings(camp)
    ready_to_allocate = add_queue_cutoffs(ranked_queue_bookings=ranked_queue_bookings, places_left=places_left)

    template_name = "cciw/officers/booking_queue.html"
    headers = {}
    if refresh_contents_only:
        # We use server side HX-Retarget here and above, because client side
        # can't set the hx-target: if form validation fails, we target a
        # different element than if it succeeds.
        headers.update({"HX-Retarget": "#id_main_content"})
        template_name = f"{template_name}#main-content"

    context = {
        "camp": camp,
        "year": camp.year,
        "last_year": camp.year - 1,
        "places_left": places_left,
        "ready_to_allocate": ready_to_allocate,
        "title": f"Booking queue - {camp.nice_name}",
        "ranked_queue_bookings": ranked_queue_bookings,
        "edit_queue_entry_mode": edit_queue_entry_mode,
    }
    return TemplateResponse(request, template_name, context, headers=headers)
