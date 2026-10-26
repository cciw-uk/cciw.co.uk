# Utilities and middleware for thread local storage
from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cciw.accounts.models import User

_thread_locals = threading.local()


def is_web_request():
    return "SERVER_PROTOCOL" in os.environ or "RUN_MAIN" in os.environ


def get_current_user() -> User:
    return getattr(_thread_locals, "user", None)


def set_current_user(user: User):
    _thread_locals.user = user


def thread_locals(get_response: Callable) -> Callable:
    """Adds various objects to thread local storage from the request object."""

    def middleware(request):
        set_current_user(getattr(request, "user", None))
        return get_response(request)

    return middleware
