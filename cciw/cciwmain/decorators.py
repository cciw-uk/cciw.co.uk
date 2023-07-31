from functools import wraps

from django.core.exceptions import ValidationError
from django.http import HttpResponse

from cciw.cciwmain.utils import python_to_json


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
                "status": "failure",
                "errors": errors,
            }
        else:
            code = 200

        if isinstance(data, HttpResponse):
            return data

        if not isinstance(data, bytes | str):
            data = python_to_json(data)
        resp = HttpResponse(data, status=code, content_type="application/json")
        resp["Cache-Control"] = "no-cache"
        return resp

    return wraps(view_func)(_inner)
