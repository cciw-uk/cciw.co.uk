# -*- coding: utf-8 -*-
"""
Utility functions and classes.

For CCIW specific utilities see cciw.cciwmain.common
"""
from datetime import date, datetime
import json
import fcntl
import operator
import os

from django.core.validators import validate_email, ValidationError
from django.utils.safestring import mark_safe
from django.utils.functional import Promise
from django.utils.encoding import force_text

def obfuscate_email(email):
    safe_email = email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ')
    return mark_safe("<span style='text-decoration: underline;'>%s</span>" % safe_email)

def modified_query_string(request, dict, fragment=''):
    """Returns the query string represented by request, with key-value pairs
    in dict added or modified.  """
    qs = request.GET.copy()
    # NB can't use qs.update(dict) here
    for k,v in dict.items():
        qs[k] = v
    return request.path + '?' + qs.urlencode() + fragment

def strip_control_chars(text):
    for i in range(0,32):
        text = text.replace(chr(i), '')
    return text

def unslugify(slug):
    "Turns dashes and underscores into spaces and applies title casing"
    return slug.replace("-", " ").replace("_", " ").title()


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


class Lock(object):

    def __init__(self, filename):
        self.filename = filename
        # This will create it if it does not exist already
        self.handle = open(filename, 'w')

    # Bitwise OR fcntl.LOCK_NB if you need a non-blocking lock
    def acquire(self):
        fcntl.flock(self.handle, fcntl.LOCK_EX)

    def release(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)

    def __del__(self):
        self.handle.close()

def is_valid_email(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    else:
        return True
