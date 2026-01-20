from collections.abc import Iterable

from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse

from cciw.bookings.models.yearconfig import get_booking_open_data
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp

from ..utils.auth import camp_admin_required
from ..utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs


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
    booking_open_data = get_booking_open_data(year=thisyear)

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
            "booking_open_data": booking_open_data,
        },
    )
