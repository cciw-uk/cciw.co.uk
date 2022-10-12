from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from furl import furl

from cciw.utils.spreadsheet import (
    ExcelFromDataFrameBuilder,
    SpreadsheetFromDataFrameBuilder,
    SpreadsheetSimpleBuilder,
    spreadsheet_simple_builders,
)


def close_window_response(request: HttpRequest, *, clear_messages=False):
    # First we clear any messages, because, due to the closed window, these will
    # otherwise appear in another window at an unrelated moment, confusing the
    # user.
    if clear_messages:
        assert request is not None
        list(messages.get_messages(request))

    # Closes the response via javascript:
    return HttpResponse(
        """<!DOCTYPE html><html><head><title>Close</title><script type="text/javascript">window.close()</script></head><body></body></html>"""
    )


def reroute_response(request: HttpRequest, default_to_close=True):
    """
    Utility for rerouting (or closing window) at the end of a page being used.
    """
    # if '_temporary_window=1 in query string, that overrides everything
    # - we should close the window.
    if request.GET.get("_temporary_window", "") == "1":
        return close_window_response(request, clear_messages=True)

    # if we have a safe return to URL, do a redirect
    if "_return_to" in request.GET:
        url = request.GET["_return_to"]
        if url_has_allowed_host_and_scheme(url, settings.ALLOWED_HOSTS):
            return HttpResponseRedirect(url)

    # Otherwise close the window
    if default_to_close:
        return close_window_response(request, clear_messages=True)
    else:
        return None


def user_passes_test_improved(test_func):
    """
    Like user_passes_test, but doesn't redirect user to login screen if they are
    already logged in.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs):
            user = request.user
            if user.is_authenticated:
                if user.is_superuser or test_func(user):
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("<h1>Access denied</h1>")

            # All unauthenticated users are blocked access, and redirected to
            # login.
            return redirect_to_login_with_next(request)

        return _wrapped_view

    return decorator


def redirect_to_login_with_next(request: HttpRequest) -> HttpResponseRedirect:
    login_url = settings.LOGIN_URL
    path = get_current_url_for_redirection(request, login_url)
    return redirect_to_url_with_next(path, login_url, REDIRECT_FIELD_NAME)


def redirect_to_password_change_with_next(request: HttpRequest) -> HttpResponseRedirect | None:
    password_change_url = reverse("admin:password_change")
    if furl(request.build_absolute_uri()).path == password_change_url:
        return None  # loop breaker
    path = get_current_url_for_redirection(request, password_change_url)
    return redirect_to_url_with_next(path, password_change_url, REDIRECT_FIELD_NAME)


def get_current_url_for_redirection(request, redirect_url):
    url = request.build_absolute_uri()
    # If the url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse(redirect_url)[:2]
    current_scheme, current_netloc = urlparse(url)[:2]
    if (not login_scheme or login_scheme == current_scheme) and (not login_netloc or login_netloc == current_netloc):
        url = request.get_full_path()
    # Otherwise we need to include scheme and location
    return url


def redirect_to_url_with_next(next_url, url, redirect_field_name) -> HttpResponseRedirect:
    f = furl(url)
    f.args[redirect_field_name] = next_url
    return HttpResponseRedirect(f.url)


def get_spreadsheet_simple_builder(request: HttpRequest) -> SpreadsheetSimpleBuilder:
    format = request.GET.get("format", "xls")
    if format not in spreadsheet_simple_builders:
        raise Http404()
    return spreadsheet_simple_builders[format]()


def get_spreadsheet_from_dataframe_builder(request: HttpRequest) -> SpreadsheetFromDataFrameBuilder:
    # We only have one choice at the moment:
    return ExcelFromDataFrameBuilder()
