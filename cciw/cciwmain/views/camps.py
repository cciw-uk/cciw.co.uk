from datetime import date

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp


def index(request: HttpRequest, year: int | None = None) -> TemplateResponse:
    """
    Displays a list of all camps, or all camps in a given year.
    """
    camps = Camp.objects.order_by("-year", "start_date")
    if year is not None:
        camps = camps.filter(year=year)
        if len(camps) == 0:
            raise Http404

    return TemplateResponse(
        request,
        "cciw/camps/index.html",
        {
            "title": "Camp information",
            "camps": camps,
        },
    )


def detail(request: HttpRequest, year: int, slug: str) -> TemplateResponse:
    """
    Shows details of a specific camp.
    """
    from cciw.bookings.models import get_booking_open_data

    camp = get_object_or_404(Camp.objects.all(), year=year, camp_name__slug=slug)

    return TemplateResponse(
        request,
        "cciw/camps/detail.html",
        {
            "camp": camp,
            "title": camp.nice_name + camp.bracketted_old_name,
            "booking_open_data": get_booking_open_data(camp.year),
            "today": date.today(),
            "breadcrumb": (
                common.create_breadcrumb(
                    [format_html('<a href="{0}">See all camps</a>', reverse("cciw-cciwmain-camps_index"))]
                )
                if camp.is_past()
                else None
            ),
        },
    )


def thisyear(request: HttpRequest) -> TemplateResponse:
    year = common.get_thisyear()
    return TemplateResponse(
        request,
        "cciw/camps/thisyear.html",
        {
            "title": f"Camps {year}",
            "camps": Camp.objects.filter(year=year).order_by("site__short_name", "start_date"),
        },
    )
