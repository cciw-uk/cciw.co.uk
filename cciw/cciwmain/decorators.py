from urllib.parse import urlencode
from functools import wraps

from django.http import HttpResponse
from django.shortcuts import render

from cciw.cciwmain.utils import python_to_json


def login_redirect(path):
    """Returns a URL for logging in and then redirecting to the supplied path"""
    qs = urlencode({'redirect': path})
    return '%s?%s' % ('/login/', qs)

LOGIN_FORM_KEY = 'this_is_the_login_form'
ERROR_MESSAGE = "Please enter a correct username and password. Note that both fields are case-sensitive."


def _display_login_form(request, error_message='', login_page=False):
    return render(request, 'cciw/members/login.html', {'app_path': request.get_full_path(),
                                                       'error_message': error_message,
                                                       'title': "Login"})


def email_errors_silently(func):
    """
    Decorator causes any errors raised by a function to be emailed to admins,
    and then silently ignored.
    """
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            from cciw.cciwmain.common import exception_notify_admins
            exception_notify_admins('Error on CCIW site')
            return None

    return wraps(func)(_inner)


def json_response(view_func):
    def _inner(request, *args, **kwargs):
        data = view_func(request, *args, **kwargs)
        if not isinstance(data, (bytes, str)):
            data = python_to_json(data)
        resp = HttpResponse(data,
                            content_type="application/json")
        resp['Cache-Control'] = "no-cache"
        return resp
    return wraps(view_func)(_inner)
