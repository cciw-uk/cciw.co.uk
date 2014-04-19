from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, HttpResponseForbidden

from cciw.utils.spreadsheet import ExcelFormatter


def close_window_response():
    return HttpResponse("""<!DOCTYPE html><html><head><title>Close</title><script type="text/javascript">window.close()</script></head><body></body></html>""")


def user_passes_test_improved(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Like user_passes_test, but doesn't redirect user to login screen if they are
    already logged in.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            if request.user.is_authenticated():
                return HttpResponseForbidden("<h1>Access denied</h1>")

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


formatters = {'xls': ExcelFormatter}

def get_spreadsheet_formatter(request):
    format = request.GET.get('format', 'xls')
    if format not in formatters:
        raise Http404
    return formatters[format]()
