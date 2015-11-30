# Utilities and middleware for thread local storage
import threading
import os


_thread_locals = threading.local()


def is_web_request():
    return 'SERVER_PROTOCOL' in os.environ or \
           'RUN_MAIN' in os.environ


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    _thread_locals.user = user


class ThreadLocals(object):
    """Adds various objects to thread local storage from the request object."""
    def process_request(self, request):
        set_current_user(getattr(request, 'user', None))
