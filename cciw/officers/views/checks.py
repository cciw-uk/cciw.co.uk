from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from django.http import HttpRequest, HttpResponse

from cciw.utils.functional import func_name

if TYPE_CHECKING:
    from cciw.utils.views import ViewFunc


def check_officers_views[**P](view_func: ViewFunc[P]) -> ViewFunc[P]:
    """
    Checks the decorators applied to officers view functions
    """
    from cciw.officers.models.data_retention import NoDataRelation
    from cciw.officers.views.utils.data_retention import DOWNLOAD_HAS_BEEN_LOGGED, SensitiveDownloadResponse
    from cciw.utils.views import USER_AUTH_DECORATOR_APPLIED

    # Check 1:
    # view function should have had security decorator applied.
    view_func_name = func_name(view_func)
    if not getattr(view_func, USER_AUTH_DECORATOR_APPLIED, False):
        # Sometimes the assertion is swallowed (?) so we print it
        message = f"{view_func_name} needs to have one of the `user_passes_test_improved` decorators applied"
        raise AssertionError(message)

    @wraps(view_func)
    def wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        resp = view_func(request, *args, **kwargs)
        # Check 2:
        # - if the response is a SensitiveDownloadResponse,
        #   and the data relation was not `NoDataRelation`,
        #   then the download should have been logged.

        if isinstance(resp, SensitiveDownloadResponse) and not isinstance(resp.data_relation, NoDataRelation):
            if not getattr(resp, DOWNLOAD_HAS_BEEN_LOGGED, False):
                raise AssertionError(f"Sensitive download wasn't logged, bug in {view_func_name}")

        return resp

    return wrapped
