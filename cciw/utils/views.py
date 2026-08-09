import copy
import json
import typing
from collections.abc import Callable
from functools import wraps
from typing import Concatenate
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseRedirect, QueryDict
from django.template.response import TemplateResponse
from django.urls import reverse
from django.urls.resolvers import ResolverMatch, get_resolver
from django.utils.http import url_has_allowed_host_and_scheme
from furl import furl

from cciw.accounts.models import User
from cciw.utils.functional import func_name

type ViewFunc[**P] = Callable[Concatenate[HttpRequest, P], HttpResponse]
type TemplateResponseViewFunc[**P] = Callable[Concatenate[HttpRequest, P], TemplateResponse]

USER_AUTH_DECORATOR_APPLIED = "USER_AUTH_DECORATOR_APPLIED"


def close_window_response(request: HttpRequest, *, clear_messages=False) -> HttpResponse:
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


def reroute_response(request: HttpRequest, *, default_to_close: bool = True) -> HttpResponse | None:
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


def user_passes_test_improved[**P](
    test_func: Callable[[User], bool],
) -> Callable[[ViewFunc[P]], ViewFunc[P]]:
    """
    Like user_passes_test, but doesn't redirect user to login screen if they are
    already logged in.
    """

    def decorator(view_func: ViewFunc[P]) -> ViewFunc[P]:
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
            user = request.user
            if user.is_authenticated:
                if user.is_superuser or test_func(user):
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("<h1>Access denied</h1>")

            # All unauthenticated users are blocked access, and redirected to
            # login.
            return redirect_to_login_with_next(request)

        setattr(_wrapped_view, USER_AUTH_DECORATOR_APPLIED, True)
        return _wrapped_view

    return decorator


def anonymous_allowed[V: ViewFunc](view_func: V) -> V:
    setattr(view_func, USER_AUTH_DECORATOR_APPLIED, True)
    return view_func


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


# MAYBE combine these utilities that check redirect URLs, we've got slightly
# different patterns going on.


def validated_redirect_response(
    *, requested_redirect_url: str | list | None, default_redirect_url: str
) -> HttpResponseRedirect:
    if isinstance(requested_redirect_url, str) and url_has_allowed_host_and_scheme(
        url=requested_redirect_url,
        allowed_hosts=settings.ALLOWED_HOSTS,
    ):
        return HttpResponseRedirect(requested_redirect_url)
    return HttpResponseRedirect(default_redirect_url)


def get_current_url_for_redirection(request: HttpRequest, redirect_url: str) -> str:
    url = request.build_absolute_uri()
    # If the url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse(redirect_url)[:2]
    current_scheme, current_netloc = urlparse(url)[:2]
    if (not login_scheme or login_scheme == current_scheme) and (not login_netloc or login_netloc == current_netloc):
        url = request.get_full_path()
    # Otherwise we need to include scheme and location
    return url


def get_redirect_from_request(request: HttpRequest) -> HttpResponse:
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, "")
    if redirect_to:
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=settings.ALLOWED_HOSTS,
            require_https=request.is_secure(),
        )
        if url_is_safe and urlparse(redirect_to).path != request.path:
            return HttpResponseRedirect(redirect_to)
    return None


def redirect_to_url_with_next(next_url: str, url: str, redirect_field_name: str) -> HttpResponseRedirect:
    f = furl(url)
    f.args[redirect_field_name] = next_url
    return HttpResponseRedirect(f.url)


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


def htmx_redirect(url):
    return HttpResponse(headers={"HX-Redirect": url})


def for_htmx[V: ViewFunc](
    *,
    use_partial_from_params: bool = False,
) -> Callable[[V], V]:
    """
    If the request is from htmx, then render a partial page, using either:

    - the partial specified in GET/POST parameter "use_partial", if `use_partial_from_params=True` is passed
    - more options in the future?
    """
    if len([p for p in [use_partial_from_params] if p]) != 1:
        raise ValueError("You must pass exactly one of 'use_partial_from_params=True'")

    def decorator(view: V) -> V:
        @wraps(view)
        def _view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            resp: HttpResponse = view(request, *args, **kwargs)
            if request.headers.get("Hx-Request", False):
                if not isinstance(resp, TemplateResponse):
                    if not resp.content and any(
                        h in resp.headers
                        for h in (
                            "Hx-Trigger",
                            "Hx-Trigger-After-Swap",
                            "Hx-Trigger-After-Settle",
                            "Hx-Redirect",
                        )
                    ):
                        # This is a special case response with no body, that is
                        # sent only because of some htmx headers. It doesn't
                        # need modifying and can just be returned.
                        return resp
                    # Otherwise there is some mistake
                    raise ValueError(f"Cannot modify a response of type {type(resp)} that isn't a TemplateResponse")

                if resp.is_rendered:
                    raise ValueError("Cannot modify a response that has already been rendered")

                partials_to_use: list[str] | None = None
                if use_partial_from_params:
                    use_partial_from_params_val = _get_param_from_request(request, "use_partial")
                    if use_partial_from_params_val is not None and len(use_partial_from_params_val) > 0:
                        partials_to_use = use_partial_from_params_val

                if partials_to_use is not None:
                    if len(partials_to_use) == 1:
                        resp.template_name = resp.template_name + "#" + partials_to_use[0]
                        return resp
                    else:
                        # Need to render multiple times.
                        content = []
                        for partial in partials_to_use:
                            part = TemplateResponse(
                                request,
                                resp.template_name + "#" + partial,
                                context=resp.context_data,
                            )
                            part.render()
                            content.append(part.content)
                        return HttpResponse(content=b"".join(content))

            return resp

        return typing.cast(V, _view)

    return decorator


def add_hx_trigger_header(response: HttpResponse, events: dict) -> HttpResponse:
    if events:
        response.headers["Hx-Trigger"] = json.dumps(events)
    return response


def url_matches_view_function(url: str, function: ViewFunc) -> bool:
    # TODO
    # - shouldn't raise error if no match found
    # - strip query parameters
    match: ResolverMatch = get_resolver().resolve(url)
    if match is not None and func_name(match.func) == func_name(function):
        return True

    return False
