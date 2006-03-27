# Utilities and middleware for thread local storage
import threading

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class ThreadLocals(object):
    """Adds various objects to thread local storage from the request object."""
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
