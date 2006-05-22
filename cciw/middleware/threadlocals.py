# Utilities and middleware for thread local storage
import threading
import datetime

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_member():
    """Returns the currently logged in member, or None"""
    return getattr(_thread_locals, 'member', None)

def set_current_member(member):
    # This is *very* rarely needed.
    _thread_locals.member = member

def _get_member_from_request(request):
    from cciw.cciwmain.models import Member
    try:
        return Member.objects.get(user_name=request.session['member_id'])
    except (KeyError, Member.DoesNotExist):
        return None

class ThreadLocals(object):
    """Adds various objects to thread local storage from the request object."""
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        
        member = _get_member_from_request(request)
        if member is not None:
            # use opportunity to update last_seen data
            if (member.last_seen is None) or (datetime.datetime.now() - member.last_seen).seconds > 60:
                member.last_seen = datetime.datetime.now()
                member.save()
        set_current_member(member)

