from functools import wraps

from django.core.exceptions import ValidationError
from django.http import HttpResponse

from cciw.cciwmain.utils import python_to_json


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
        try:
            data = view_func(request, *args, **kwargs)
        except ValidationError as e:
            errors = {}
            for f, vs in e.error_dict.items():
                errors[f] = [v.message for v in vs]
            code = 400
            data = {
                'status': 'failure',
                'errors': errors,
            }
        else:
            code = 200

        if isinstance(data, HttpResponse):
            return data

        if not isinstance(data, (bytes, str)):
            data = python_to_json(data)
        resp = HttpResponse(data,
                            status=code,
                            content_type="application/json")
        resp['Cache-Control'] = "no-cache"
        return resp
    return wraps(view_func)(_inner)
