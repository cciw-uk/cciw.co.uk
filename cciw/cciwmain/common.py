"""
Utility functions and base classes that are common to all views etc.
"""
import re
from datetime import date, timedelta
from functools import wraps

import attr
from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html_join

from cciw.cciwmain.forms import render_single_form_field


@attr.s(auto_attribs=True)
class CampId:
    year: int
    slug: str

    def __str__(self):
        # This has to be the inverse of CampIdConverter.to_python and match
        # CampIdConverter.regex
        return f"{self.year}-{self.slug}"


def htmx_form_validate(*, form_class: type):
    """
    Instead of a normal view, just do htmx validation using the given form class,
    for a single field and return the single div that needs to be replaced.
    Normally the form class will be the same class used in the view body.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if (
                request.method == "GET"
                and "Hx-Request" in request.headers
                and (htmx_validation_field := request.GET.get("_validate_field", None))
            ):
                form = form_class(request.GET)
                form.is_valid()  # trigger validation
                return HttpResponse(render_single_form_field(form, htmx_validation_field, validation_only=True))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


_thisyear = None
_thisyear_timestamp = None


def get_thisyear():
    """
    Get the year the website is currently on.  The website year is
    equal to the year of the last camp in the database, or the year
    afterwards if that camp is at least 30 days in the past.
    (30 days, to give a leaders the chance to access the leader
    area after their camp is finished).
    """
    global _thisyear, _thisyear_timestamp
    if _thisyear is None or _thisyear_timestamp is None or (timezone.now() - _thisyear_timestamp).seconds > 3600:
        from cciw.cciwmain.models import Camp

        try:
            lastcamp = Camp.objects.prefetch_related(None).order_by("-end_date")[0]
        except IndexError:
            return timezone.now().year
        if lastcamp.end_date + timedelta(days=30) <= date.today():
            _thisyear = lastcamp.year + 1
        else:
            _thisyear = lastcamp.year
        _thisyear_timestamp = timezone.now()
    return _thisyear


def standard_subs(value):
    """Standard substitutions made on HTML content"""
    return (
        value.replace("{{thisyear}}", str(get_thisyear()))
        .replace("{{media}}", settings.MEDIA_URL)
        .replace("{{static}}", settings.STATIC_URL)
    )


# This assumes our substitutions don't introduce anything that must be escaped
standard_subs.is_safe = True


def create_breadcrumb(links):
    return format_html_join(" :: ", "{0}", ((link,) for link in links))


def standard_processor(request):
    """
    Processor that does standard processing of request that we need for all
    pages.
    """
    context = {}
    format = request.GET.get("format")
    if format is not None:
        # json or atom - we are not rendering typical pages, and don't want the
        # overhead of additional queries. This is especially important for Atom,
        # which can render many templates with separate RequestContext
        # instances.
        return context

    from cciw.sitecontent.models import MenuLink

    thisyear = get_thisyear()
    context["thisyear"] = thisyear
    assert isinstance(request.path, str)
    context["homepage"] = request.path == "/"

    # Ugly special casing for 'thisyear' camps
    m = re.match(rf"/camps/{thisyear}/(\d+)/", request.path)
    if m is not None:
        request_path = f"/thisyear/{m.groups()[0]}/"
    else:
        request_path = request.path

    # As a callable, get_links will get called automatically by the template
    # renderer *when needed*, so we avoid queries. We memoize in links_cache to
    # avoid double queries
    links_cache = []

    def get_links():
        if len(links_cache) > 0:
            return links_cache
        else:
            for link in MenuLink.objects.filter(parent_item__isnull=True, visible=True):
                link.title = standard_subs(link.title)
                link.is_current_page = False
                link.is_current_section = False
                if link.url == request_path:
                    link.is_current_page = True
                elif request_path.startswith(link.url) and link.url != "/":
                    link.is_current_section = True
                links_cache.append(link)
            return links_cache

    context["menulinks"] = get_links
    context["PRODUCTION"] = settings.LIVEBOX

    return context


def get_current_domain():
    return Site.objects.get_current().domain
