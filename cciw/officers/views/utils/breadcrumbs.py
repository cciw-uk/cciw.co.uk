from collections.abc import Callable
from functools import wraps

from django.http import HttpResponse
from django.template.response import TemplateResponse

type NamedUrl = str
type BreadCrumb = tuple[NamedUrl | None, str]


def with_breadcrumbs(breadcrumbs: list[BreadCrumb]) -> Callable:
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs) -> HttpResponse:
            retval = func(request, *args, **kwargs)
            if isinstance(retval, TemplateResponse):
                retval.context_data["breadcrumbs"] = breadcrumbs
            return retval

        return wrapper

    return decorator


officers_breadcrumbs: list[BreadCrumb] = [("cciw-officers-index", "Officer home page")]
leaders_breadcrumbs: list[BreadCrumb] = officers_breadcrumbs + [("cciw-officers-leaders_index", "Leaders' tools")]
