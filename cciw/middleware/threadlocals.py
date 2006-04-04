# Utilities and middleware for thread local storage
import threading
import datetime

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_member():
    """Returns the currently logged in member, or None"""
    return getattr(_thread_locals, 'member', None)

class ThreadLocals(object):
    """Adds various objects to thread local storage from the request object."""
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        
        try:
            from cciw.cciwmain.models import Member
            member = Member.objects.get(user_name=request.session['member_id'])
            # use opportunity to update last_seen data
            if (datetime.datetime.now() - member.last_seen).seconds > 60:
                member.last_seen = datetime.datetime.now()
                member.save()
        except (KeyError, Member.DoesNotExist):
            member = None
        _thread_locals.member = member

