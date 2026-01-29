from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from cciw.accounts.models import User
from cciw.bookings.models import most_recent_booking_year
from cciw.cciwmain import common
from cciw.utils.views import get_redirect_from_request

from .booking_secretary import BOOKING_STATS_PREVIOUS_YEARS


# /officers/
@staff_member_required
@never_cache
def index(request: HttpRequest) -> TemplateResponse:
    """Displays a list of links/buttons for various actions."""

    # Handle redirects, since this page is LOGIN_URL
    redirect_resp = get_redirect_from_request(request)
    if redirect_resp is not None:
        return redirect_resp

    user: User = request.user
    context: dict = {
        "title": "Officer home page",
    }
    context["thisyear"] = common.get_thisyear()
    context["lastyear"] = context["thisyear"] - 1
    if user.is_camp_admin or user.is_superuser:
        context["show_leader_links"] = True
        context["show_admin_link"] = True
        context["show_visitor_book_links"] = True
    if user.is_cciw_secretary or user.is_superuser:
        context["show_secretary_links"] = True
        context["show_admin_link"] = True
    if user.is_dbs_officer or user.is_camp_admin or user.is_superuser:
        context["show_dbs_officer_links"] = True
    if user.is_booking_secretary or user.is_superuser:
        context["show_booking_secretary_links"] = True
    if user.is_booking_secretary or user.is_treasurer or user.is_superuser:
        context["show_booking_report_links"] = True
    if user.is_committee_member or user.is_booking_secretary or user.is_superuser:
        context["show_secretary_and_committee_links"] = True
        booking_year = most_recent_booking_year()
        if booking_year is not None:
            context["booking_stats_end_year"] = booking_year
            context["booking_stats_start_year"] = booking_year - BOOKING_STATS_PREVIOUS_YEARS
        context["show_visitor_book_links"] = True

    return TemplateResponse(request, "cciw/officers/index.html", context)
