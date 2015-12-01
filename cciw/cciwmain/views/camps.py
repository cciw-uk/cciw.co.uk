from datetime import date

from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.utils.html import format_html

from cciw.cciwmain.common import create_breadcrumb, get_thisyear
from cciw.cciwmain.models import Camp


def index(request, year=None):
    """
    Displays a list of all camps, or all camps in a given year.

    Template - ``cciw/camps/index.html``

    Context:
        camps
            List of all Camp objects (or all Camp objects in the specified year).
    """
    c = {}
    c['title'] = "Camp information"
    all_camps = Camp.objects.filter(end_date__lte=date.today())
    if (year is None):
        camps = all_camps.order_by('-year', 'start_date')
    else:
        year = int(year)  # year is result of regex match
        camps = all_camps.filter(year=year)\
                         .order_by('-year', 'start_date')
        if len(camps) == 0:
            raise Http404
    c['camps'] = camps

    return render(request, 'cciw/camps/index.html', c)


def detail(request, year, slug):
    """
    Shows details of a specific camp.

    Context:
        camp
            Camp objects
        camp_is_past
            True if this camp is now finished.
    """
    from cciw.bookings.models import is_booking_open

    try:
        camp = Camp.objects.get(year=int(year), camp_name__slug=slug)
    except Camp.DoesNotExist:
        raise Http404

    c = {}
    c['camp'] = camp
    c['title'] = camp.nice_name

    if camp.is_past():
        c['breadcrumb'] = create_breadcrumb(
            [format_html('<a href="{0}">Camps</a>',
                         reverse("cciw-cciwmain-camps_index")),
             camp.nice_name]
        )

    c['is_booking_open'] = is_booking_open(camp.year)
    c['today'] = date.today()

    return render(request, 'cciw/camps/detail.html', c)


def thisyear(request):
    c = dict(title="Camps %d" % get_thisyear())
    c['camps'] = Camp.objects.filter(year=get_thisyear()).order_by('site__short_name', 'start_date')
    return render(request, 'cciw/camps/thisyear.html', c)
