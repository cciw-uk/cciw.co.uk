from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.utils.http import is_safe_url

from cciw.utils.spreadsheet import ExcelFormatter, OdsFormatter


def close_window_response(request=None, clear_messages=False):
    # First we clear any messages, because, due to the closed window, these will
    # otherwise appear in another window at an unrelated moment, confusing the
    # user.
    if clear_messages:
        assert request is not None
        list(messages.get_messages(request))

    # Closes the response via javascript:
    return HttpResponse("""<!DOCTYPE html><html><head><title>Close</title><script type="text/javascript">window.close()</script></head><body></body></html>""")


def reroute_response(request, default_to_close=True):
    """
    Utility for rerouting (or closing window) at the end of a page being used.
    """
    # if '_temporary_window=1 in query string, that overrides everything
    # - we should close the window.
    if request.GET.get('_temporary_window', '') == '1':
        return close_window_response(request=request, clear_messages=True)

    # if we have a safe return to URL, do a redirect
    if '_return_to' in request.GET:
        url = request.GET['_return_to']
        if is_safe_url(url=url):
            return HttpResponseRedirect(url)

    # Otherwise close the window
    if default_to_close:
        return close_window_response(request=request, clear_messages=True)
    else:
        return None


def user_passes_test_improved(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Like user_passes_test, but doesn't redirect user to login screen if they are
    already logged in.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                if test_func(request.user):
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("<h1>Access denied</h1>")

            # All unauthenticated users are blocked access, and redirected to
            # login.
            path = request.build_absolute_uri()
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(login_url or
                                                  settings.LOGIN_URL)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            return redirect_to_login(path, login_url, redirect_field_name)
        return _wrapped_view
    return decorator


formatters = {
    'xls': ExcelFormatter,
    'ods': OdsFormatter,
}


def get_spreadsheet_formatter(request):
    format = request.GET.get('format', 'xls')
    if format not in formatters:
        raise Http404()
    return formatters[format]()
