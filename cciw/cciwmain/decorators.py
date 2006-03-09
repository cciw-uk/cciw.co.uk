from cciw.cciwmain.common import get_current_member
from django.http import HttpResponseRedirect, HttpResponseForbidden
from cciw.cciwmain.models import Permission
import urllib

def member_required(func):
    """Decorator that redirects to a login screen if the user isn't logged in."""
    def _check(request, *args, **kwargs):
        if get_current_member(request) is None:
            qs = urllib.urlencode({'redirect': request.path})
            return HttpResponseRedirect('%s?%s' % ('/login/', qs))
        else:
            return func(request, *args, **kwargs)
    return _check

def same_member_required(member_name_arg):
    """Returns a decorator for a view that only allows the specified
    member to view the page.
    
    member_name_arg is the argument to the wrapped function 
    that contains the users name. It is either an integer for a positional 
    argument or a string for a keyword argument."""
    
    def _dec(func):
        def _check(request, *args, **kwargs):
            if isinstance(member_name_arg, int):
                # positional argument, but out by one
                # due to the request arg
                user_name = args[member_name_arg-1]
            else:
                user_name = kwargs[member_name_arg]
            cur_member = get_current_member(request)
            if cur_member is None or \
                (cur_member.user_name != user_name and 
                not member.has_perm(Permission.SUPERUSER)):
                return HttpResponseForbidden('<h1>Access denied</h1>')
            return func(request, *args, **kwargs)
        return _check
    return _dec
