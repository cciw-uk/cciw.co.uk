from collections.abc import Iterable

from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from cciw.accounts.models import User
from cciw.bookings.models import most_recent_booking_year
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.utils.views import get_redirect_from_request

from .booking_secretary import BOOKING_STATS_PREVIOUS_YEARS
from .utils.auth import (
    camp_admin_required,
)
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs


# /officers/
@staff_member_required
@never_cache
def index(request):
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


@staff_member_required
@camp_admin_required
@with_breadcrumbs(officers_breadcrumbs)
def leaders_index(request):
    """Displays a list of links for actions for leaders"""
    user = request.user
    thisyear = common.get_thisyear()
    show_all = "show_all" in request.GET
    camps: Iterable[Camp] = Camp.objects.all().include_other_years_info()
    if not show_all:
        camps = camps.filter(id__in=[c.id for c in user.camps_as_admin_or_leader])
    last_existing_year = Camp.objects.order_by("-year")[0].year

    return TemplateResponse(
        request,
        "cciw/officers/leaders_index.html",
        {
            "title": "Leader's tools",
            "current_camps": [c for c in camps if c.year == thisyear],
            "old_camps": [c for c in camps if c.year < thisyear],
            "statsyears": list(range(last_existing_year, last_existing_year - 3, -1)),
            "stats_end_year": last_existing_year,
            "stats_start_year": 2006,  # first year this feature existed
            "show_all": show_all,
        },
    )
