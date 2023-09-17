from functools import wraps
from typing import TypeAlias

from django.http import HttpResponse
from django.template.response import TemplateResponse

NamedUrl: TypeAlias = str
BreadCrumb = tuple[NamedUrl, str]


def with_breadcrumbs(breadcrumbs: list[BreadCrumb]):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs) -> HttpResponse:
            retval = func(request, *args, **kwargs)
            if isinstance(retval, TemplateResponse):
                retval.context_data["breadcrumbs"] = breadcrumbs
            return retval

        return wrapper

    return decorator


officers_breadcrumbs = [("cciw-officers-index", "Officer home page")]
leaders_breadcrumbs = officers_breadcrumbs + [("cciw-officers-leaders_index", "Leaders' tools")]
