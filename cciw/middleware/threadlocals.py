# Utilities and middleware for thread local storage
import threading
import datetime
import os

_thread_locals = threading.local()

def is_web_request():
    return os.environ.has_key('SERVER_PROTOCOL') or \
           os.environ.has_key('RUN_MAIN')

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def set_current_user(user):
    _thread_locals.user = user

def get_current_member():
    """Returns the currently logged in member, or None"""
    return getattr(_thread_locals, 'member', None)

def set_current_member(member):
    _thread_locals.member = member

def _get_member_from_request(request):
    from cciw.cciwmain.models import Member
    try:
        return Member.objects.get(user_name=request.session['member_id'])
    except (KeyError, Member.DoesNotExist):
        return None

def set_member_session(request, member):
    request.session['member_id'] = member.user_name
    set_current_member(member)

def remove_member_session(request):
    del request.session['member_id']
    del _thread_locals.member

class ThreadLocals(object):
    """Adds various objects to thread local storage from the request object."""
    def process_request(self, request):
        set_current_user(getattr(request, 'user', None))

        member = _get_member_from_request(request)
        if member is not None:
            # use opportunity to update last_seen data
            if (member.last_seen is None) or (datetime.datetime.now() - member.last_seen).seconds > 60:
                member.last_seen = datetime.datetime.now()
                member.save()
        set_current_member(member)

