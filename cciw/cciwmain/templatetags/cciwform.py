from django import template
from django.utils.html import format_html, mark_safe

register = template.Library()


@register.simple_tag
def cciw_form_field(form, field_name, label):
    """
    Display a single field in the standard CCIW format.
    """
    # Assumes form has CciwFormMixin as a base

    top_errors, hidden_fields = [], []  # these will be discarded.
    return mark_safe(form.start_template +
                     form.render_field(field_name, form.fields[field_name],
                                       top_errors, hidden_fields, label_text=label) +
                     form.end_template)


@register.simple_tag(takes_context=True)
def return_to_here(context):
    request = context['request']
    return format_html('<input type="hidden" name="_return_to" value="{0}" />'
                       .format(request.get_full_path()))
