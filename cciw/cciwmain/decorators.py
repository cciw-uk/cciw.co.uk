from cciw.middleware.threadlocals import get_current_member
from django.http import HttpResponseRedirect, HttpResponseForbidden
from cciw.cciwmain.models import Permission
import urllib

def login_redirect(path):
    """Returns a URL for logging in and then redirecting to the supplied path"""
    qs = urllib.urlencode({'redirect': path})
    return '%s?%s' % ('/login/', qs)

def member_required(func):
    """Decorator for a view function that redirects to a login
     screen if the user isn't logged in."""
    def _check(request, *args, **kwargs):
        if get_current_member() is None:
            return HttpResponseRedirect(login_redirect(request.get_full_path()))
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
            cur_member = get_current_member()
            if cur_member is None or \
                (cur_member.user_name != user_name):
                return HttpResponseForbidden('<h1>Access denied</h1>')
            return func(request, *args, **kwargs)
        return _check
    return _dec
