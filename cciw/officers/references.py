"""
Utilities for dealing with Reference and Reference
"""
from django import template


def first_letter_cap(s):
    return s[0].upper() + s[1:]


def reference_present_val(v):
    # presentation function
    if v is False:
        return "No"
    elif v is True:
        return "Yes"
    else:
        return v


_REFERENCE_FORM_TEXT_TEMPLATE = """{% load reference_utils %}{% autoescape off %}{% for name, val in info %}
{{ name|wordwrap:65 }}

{{ val|wordwrap:62|indent:3 }}
{% endfor %}{% endautoescape %}"""


def reference_to_text(reference):
    c = template.Context({'info': reference.reference_display_fields()})
    return template.Template(_REFERENCE_FORM_TEXT_TEMPLATE).render(c)
