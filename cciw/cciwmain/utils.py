# -*- coding: utf-8 -*-
"""
Utility functions and classes.

For CCIW specific utilities see cciw.cciwmain.common
"""
from datetime import date
import json
import fcntl

from django.core.validators import validate_email, ValidationError
from django.utils.functional import Promise
from django.utils.encoding import force_text


# form.errors contains strings marked for translation,
# even though USE_I18N==False.  We have to do this so
# that we can serialize
class LazyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        elif isinstance(obj, date):
            # The format we need for filling in date fields:
            return obj.strftime('%Y-%m-%d')
        return obj

json_encoder = LazyEncoder(ensure_ascii=False)


def python_to_json(obj):
    return json_encoder.encode(obj)


def is_valid_email(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    else:
        return True
