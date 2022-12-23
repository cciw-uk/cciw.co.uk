import copy
from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.http.request import HttpRequest, QueryDict
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from furl import furl
from render_block import render_block_to_string

from cciw.utils.spreadsheet import ExcelFromDataFrameBuilder, ExcelSimpleBuilder


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


def get_redirect_from_request(request):
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, "")
    if redirect_to:
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=request.get_host(),
            require_https=request.is_secure(),
        )
        if url_is_safe and urlparse(redirect_to).path != request.path:
            return HttpResponseRedirect(redirect_to)
    return None


def redirect_to_url_with_next(next_url, url, redirect_field_name) -> HttpResponseRedirect:
    f = furl(url)
    f.args[redirect_field_name] = next_url
    return HttpResponseRedirect(f.url)


def get_spreadsheet_simple_builder(request: HttpRequest) -> ExcelSimpleBuilder:
    return ExcelSimpleBuilder()


def get_spreadsheet_from_dataframe_builder(request: HttpRequest) -> ExcelFromDataFrameBuilder:
    return ExcelFromDataFrameBuilder()


def for_htmx(
    *,
    if_hx_target: str | None = None,
    use_template: str | None = None,
    use_block: str | list[str] | None = None,
    use_block_from_params: bool = False,
):
    """
    If the request is from htmx, then render a partial page, using either:
    - the template specified in `use_template` param
    - the block specified in `use_block` param
    - the block specified in GET/POST parameter "use_block", if `use_block_from_params=True` is passed
    If the optional `if_hx_target` parameter is supplied, the
    hx-target header must match the supplied value as well in order
    for this decorator to be applied.
    """
    if len([p for p in [use_block, use_template, use_block_from_params] if p]) != 1:
        raise ValueError("You must pass exactly one of 'use_template', 'use_block' or 'use_block_from_params=True'")

    def decorator(view):
        @wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            if request.headers.get("Hx-Request", False):
                if if_hx_target is None or request.headers.get("Hx-Target", None) == if_hx_target:
                    blocks_to_use = use_block
                    if not hasattr(resp, "render"):
                        raise ValueError(f"Cannot modify a response of type {type(resp)} that isn't a TemplateResponse")
                    if resp.is_rendered:
                        raise ValueError("Cannot modify a response that has already been rendered")

                    if use_block_from_params:
                        use_block_from_params_val = _get_param_from_request(request, "use_block")
                        if use_block_from_params_val is None:
                            return HttpResponse("No `use_block` in request params", status="400")

                        blocks_to_use = use_block_from_params_val

                    if use_template is not None:
                        resp.template_name = use_template
                    elif blocks_to_use is not None:
                        if not isinstance(blocks_to_use, list):
                            blocks_to_use = [blocks_to_use]
                        rendered_blocks = [
                            render_block_to_string(resp.template_name, b, context=resp.context_data, request=request)
                            for b in blocks_to_use
                        ]
                        # Create new simple HttpResponse as replacement
                        resp = HttpResponse(
                            content="".join(rendered_blocks), status=resp.status_code, headers=resp.headers
                        )

            return resp

        return _view

    return decorator


def _get_param_from_request(request: HttpRequest, param) -> list[str] | None:
    """
    Checks GET then POST params for specified param
    """
    if param in request.GET:
        return request.GET.getlist(param)
    elif request.method == "POST" and param in request.POST:
        return request.POST.getlist(param)
    return None


def make_get_request(request: HttpRequest) -> HttpRequest:
    """
    Returns a new GET request based on passed in request.
    """
    new_request = copy.copy(request)
    new_request.POST = QueryDict()
    new_request.method = "GET"
    return new_request
