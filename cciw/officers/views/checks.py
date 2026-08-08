from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cciw.utils.views import ViewFunc


def check_officers_views[**P](view_func: ViewFunc[P]) -> ViewFunc[P]:
    """
    Checks the decorators applied to officers view functions
    """
    from cciw.utils.views import USER_AUTH_DECORATOR_APPLIED

    # Check 1:
    # view function should have had security decorator applied.
    if not getattr(view_func, USER_AUTH_DECORATOR_APPLIED, False):
        # Sometimes the assertion is swallowed (?) so we print it
        message = f"{view_func.__module__}.{view_func.__name__} needs to have one of the `user_passes_test_improved` decorators applied"
        raise AssertionError(message)

    return view_func
