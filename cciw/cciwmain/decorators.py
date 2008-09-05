from django.http import HttpResponseRedirect, HttpResponseForbidden
from django import template
from django.conf import settings
from django.shortcuts import render_to_response

from cciw.middleware.threadlocals import get_current_member, set_member_session
from cciw.cciwmain.models import Permission, Member
from cciw.cciwmain.common import standard_extra_context

import urllib
import datetime
from functools import wraps

def login_redirect(path):
    """Returns a URL for logging in and then redirecting to the supplied path"""
    qs = urllib.urlencode({'redirect': path})
    return '%s?%s' % ('/login/', qs)

LOGIN_FORM_KEY = 'this_is_the_login_form'
ERROR_MESSAGE = u"Please enter a correct username and password. Note that both fields are case-sensitive."

def _display_login_form(request, error_message='', login_page=False):
    c = template.RequestContext(request, standard_extra_context(title="Login"))
    return render_to_response('cciw/members/login.html', {
        'app_path': request.get_full_path(),
        'error_message': error_message
    }, context_instance=c)

def member_required_generic(except_methods):
    """Returns a decorator that forces a member to be logged in to access the view.
    'except_methods' is a list of strings indicated HTTP methods that can get
    through without a member logged in. e.g. ['GET'] to allow the view to be
    accessed if it isn't a POST request.
    """

    def decorator(view_func):
        """
        Decorator for views that checks if data was POSTed back and
        if so requires the user to log in.
        It is also used by the normal '/login/' view.
        """

        def _checklogin(request, *args, **kwargs):

            if request.method in except_methods or get_current_member() is not None:
                return view_func(request, *args, **kwargs)

            # If this isn't already the login page, display it.
            if not request.POST.has_key(LOGIN_FORM_KEY):
                message = u"Please log in again, because your session has expired."
                return _display_login_form(request, message)

            # Check the password.
            user_name = request.POST.get('user_name', '')
            try:
                member = Member.objects.get(user_name=user_name)
            except Member.DoesNotExist:
                return _display_login_form(request, ERROR_MESSAGE)

            else:
                # The member data is correct; log in the member in and continue.
                if member.check_password(request.POST.get('password', '')):
                    member.last_seen = datetime.datetime.now()
                    member.save()
                    set_member_session(request, member)

                    return HttpResponseRedirect(request.get_full_path())

                else:
                    return _display_login_form(request, ERROR_MESSAGE)

        return wraps(view_func)(_checklogin)

    return decorator

member_required_for_post = member_required_generic(['GET'])
member_required = member_required_generic([])
