"""
Utilities for dealing with ReferenceForm and Reference
"""
from cciw.officers.models import ReferenceForm
from django.template.loader import render_to_string
from django import template

def first_letter_cap(s):
    return s[0].upper()+s[1:]

def _present_val(v):
    # presentation function used in view_reference
    if v is False:
        return "No"
    elif v is True:
        return "Yes"
    else:
        return v

def reference_form_info(refform):
    """
    Name/value pairs for all user presentable
    information in ReferenceForm
    """
    # Avoid hard coding strings into templates by using field verbose_name from model
    return [(first_letter_cap(f.verbose_name), _present_val(getattr(refform, f.attname)))
            for f in ReferenceForm._meta.fields if f.attname not in ('id','reference_info_id')]

_REFERENCE_FORM_TEXT_TEMPLATE = """{% load reference_utils %}{% autoescape off %}{% for name, val in info %}
{{ name|wordwrap:65 }}

{{ val|wordwrap:62|indent:3 }}
{% endfor %}{% endautoescape %}"""

def reference_form_to_text(refform):
    c = template.Context({'info': reference_form_info(refform)})
    return template.Template(_REFERENCE_FORM_TEXT_TEMPLATE).render(c)
