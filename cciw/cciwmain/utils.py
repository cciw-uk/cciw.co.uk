# -*- coding: utf-8 -*-
"""
Utility functions and classes.

For CCIW specific utilities see cciw.cciwmain.common
"""
import json
import re
import unicodedata
from datetime import date

from django.conf import settings
from django.core.validators import ValidationError, validate_email
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.functional import Promise


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


def make_content_disposition_safe_filename(filename):
    # Browser compatibility mess - see
    # http://stackoverflow.com/questions/93551/how-to-encode-the-filename-parameter-of-content-disposition-header-in-http
    # Simple strategy:
    #  - for codepoints that can be decomposed into accents,
    #    remove the accents.
    #  - throw everything else that is not ascii away.
    #
    # Also throw away quotes (interferes with quoting in header) and other chars
    # that are tricky for file systems.
    value = filename.split('/')[-1]
    value = re.sub('[\\\/:\'"]', '', value)
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore')
    return value.decode('utf-8')


def get_protected_download(folder, filename):

    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename="{0}"'.format(make_content_disposition_safe_filename(filename))
    # Using X-Accel-Redirect means:
    # 1. nginx does the heavy lifting of data
    # 2. we can add document permissions if we want to.
    # 3. we don't have to expose the underlying file name, so we can
    #    have permalinks, yet without requiring the document
    #    to keep the same file name on disk.
    response['X-Accel-Redirect'] = settings.SECURE_DOWNLOAD_URL_BASE + folder + "/" + filename
    del response['Content-Type']  # Get nginx/upstream to set it
    return response
