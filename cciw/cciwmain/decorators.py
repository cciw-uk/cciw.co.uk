from django.http import HttpResponseRedirect, HttpResponseForbidden
from django import template
from django.conf import settings
from django.shortcuts import render_to_response

from cciw.middleware.threadlocals import get_current_member, set_member_session
from cciw.cciwmain.models import Permission, Member
from cciw.cciwmain.common import standard_extra_context

import urllib
import base64, datetime, md5
import cPickle as pickle

def copy_func_attrs(src, dest):
    dest.__name__ = src.__name__
    dest.__module__ = src.__module__
    dest.__doc__ = src.__doc__

def login_redirect(path):
    """Returns a URL for logging in and then redirecting to the supplied path"""
    qs = urllib.urlencode({'redirect': path})
    return '%s?%s' % ('/login/', qs)

LOGIN_FORM_KEY = 'this_is_the_login_form'
ERROR_MESSAGE = u"Please enter a correct username and password. Note that both fields are case-sensitive."
LOGIN_FORM_POST_DATA_KEY = 'login_form_post_data'

def _display_login_form(request, error_message=''):
    if request.method == 'POST' and request.POST.has_key(LOGIN_FORM_POST_DATA_KEY):
        # User has failed login BUT has previously saved post data,
        # so we propagate that data.
        post_data = request.POST[LOGIN_FORM_POST_DATA_KEY]
    else:
        # User's session must have expired; save their post data.
        post_data = _encode_post_data((request.method, request.POST))
    
    c = template.RequestContext(request, standard_extra_context(title="Login"))
    return render_to_response('cciw/members/login.html', {
        'app_path': request.path,
        'post_data': post_data,
        'error_message': error_message
    }, context_instance=c)

def _encode_post_data(data):
    pickled = pickle.dumps(data)
    pickled_md5 = md5.new(pickled + settings.SECRET_KEY).hexdigest()
    return base64.encodestring(pickled + pickled_md5)

def _decode_post_data(encoded_data):
    " Returns the original data that was stored"
    encoded_data = base64.decodestring(encoded_data)
    pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
    if md5.new(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
        from django.core.exceptions import SuspiciousOperation
        raise SuspiciousOperation, "User may have tampered with session cookie."
    return pickle.loads(pickled)

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
            
            def _forward_to_original(req):
                # helper function to go to the original view function.
                if req.POST.has_key(LOGIN_FORM_POST_DATA_KEY):
                    method, post_data = _decode_post_data(req.POST[LOGIN_FORM_POST_DATA_KEY])
                    if not post_data.has_key(LOGIN_FORM_KEY):
                        # overwrite request.POST with the saved post_data, and continue
                        req.POST = post_data
                        req.method = method
                        req.META['REQUEST_METHOD'] = method

                return view_func(req, *args, **kwargs)
            ## end helper

            if request.method in except_methods:
                return view_func(request, *args, **kwargs)

            if get_current_member() is not None:
                # The user is valid. Continue to the page.
                # NB: 2 routes to this:
                #  - either they were logged in
                #  - or they were logged out and so saw the login page.
                #    But they then logged in through a different
                #    browser tab, and so don't need to log in again.
                
                return _forward_to_original(request)

            # If this isn't already the login page, display it.
            if not request.POST.has_key(LOGIN_FORM_KEY):
                message = u"Please log in again, because your session has expired."
                if request.method == 'POST':
                    message += u"  Don't worry: Your submitted data has been saved and will be processed when you log in."
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

                    return _forward_to_original(request)

                else:
                    return _display_login_form(request, ERROR_MESSAGE)

        copy_func_attrs(view_func, _checklogin)
        return _checklogin

    return decorator

member_required_for_post = member_required_generic(['GET'])
member_required = member_required_generic([])
