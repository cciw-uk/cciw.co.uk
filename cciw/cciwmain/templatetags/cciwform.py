from django import template
from django.forms import Form

from cciw.cciwmain.forms import render_single_form_field

register = template.Library()


@register.simple_tag
def cciw_form_field(form: Form, field_name):
    """
    Display a single field in the standard CCiW format.
    """
    return render_single_form_field(form, field_name, validation_only=False)
