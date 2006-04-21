from django.http import HttpResponseRedirect, HttpResponseForbidden
from django import template
from django.conf import settings
from django.shortcuts import render_to_response

from cciw.middleware.threadlocals import get_current_member, set_current_member
from cciw.cciwmain.models import Permission, Member
from cciw.cciwmain.common import standard_extra_context

import urllib
import base64, datetime, md5
import cPickle as pickle

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


LOGIN_FORM_KEY = 'this_is_the_login_form'
ERROR_MESSAGE = "Please enter a correct username and password. Note that both fields are case-sensitive."

def _display_login_form(request, error_message=''):
    if request.POST and request.POST.has_key('post_data'):
        # User has failed login BUT has previously saved post data.
        post_data = request.POST['post_data']
    elif request.POST:
        # User's session must have expired; save their post data.
        post_data = _encode_post_data(request.POST)
    else:
        post_data = _encode_post_data({})
    
    c = template.RequestContext(request, standard_extra_context(title="Login"))
    return render_to_response('cciw/members/login.html', {
        'app_path': request.path,
        'post_data': post_data,
        'error_message': error_message
    }, context_instance=c)

    

def _encode_post_data(post_data):
    pickled = pickle.dumps(post_data)
    pickled_md5 = md5.new(pickled + settings.SECRET_KEY).hexdigest()
    return base64.encodestring(pickled + pickled_md5)

def _decode_post_data(encoded_data):
    encoded_data = base64.decodestring(encoded_data)
    pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
    if md5.new(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
        from django.core.exceptions import SuspiciousOperation
        raise SuspiciousOperation, "User may have tampered with session cookie."
    return pickle.loads(pickled)

def member_required_for_post(view_func):
    """
    Decorator for views that checks if data was POSTed back and 
    if so requires the user to log in.
    """
    def _checklogin(request, *args, **kwargs):
        if not request.POST:
            return view_func(request, *args, **kwargs)
    
        if get_current_member() is not None:
            # The user is valid. Continue to the page.
            if request.POST.has_key('post_data'):
                # User must have re-authenticated through a different window
                # or tab.
                request.POST = _decode_post_data(request.POST['post_data'])
            return view_func(request, *args, **kwargs)

        # If this isn't already the login page, display it.
        if not request.POST.has_key(LOGIN_FORM_KEY):
            if request.POST:
                message = _("Please log in again, because your session has expired. Don't worry: Your submission has been saved.")
            else:
                message = ""
            return _display_login_form(request, message)

        # Check the password.
        user_name = request.POST.get('user_name', '')
        try:
            member = Member.visible_members.get(user_name=user_name)
        except Member.DoesNotExist:
            return _display_login_form(request, ERROR_MESSAGE)

        # The member data is correct; log in the member in and continue.
        else:
            if member.check_password(request.POST.get('password', '')):
                request.session['member_id'] = member.user_name
                member.last_seen = datetime.datetime.now()
                member.save()
                set_current_member(member)
                
                if request.POST.has_key('post_data'):
                    post_data = _decode_post_data(request.POST['post_data'])
                    if post_data and not post_data.has_key(LOGIN_FORM_KEY):
                        # overwrite request.POST with the saved post_data, and continue
                        request.POST = post_data
                    return view_func(request, *args, **kwargs)
            else:
                return _display_login_form(request, ERROR_MESSAGE)

    return _checklogin

def same_member_required(member_name_arg):
    """Returns a decorator for a view that only allows the specified
    member to view the page.
    
    member_name_arg sepcifies the argument to the wrapped function 
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
