from django import template
from django.forms import Form
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def cciw_form_field(form: Form, field_name, label_text):
    """
    Display a single field in the standard CCiW format.
    """
    # Assumes form has CciwFormMixin as a base
    bound_field = form[field_name]
    return form.render(
        context={
            "field": bound_field,
            "errors": form.error_class(bound_field.errors, renderer=form.renderer),
            "label_tag": bound_field.label_tag(contents=label_text),
        },
        template_name=form.template_name_p_formrow,
    )


@register.simple_tag(takes_context=True)
def return_to_here(context):
    request = context["request"]
    return format_html('<input type="hidden" name="_return_to" value="{0}" />', request.get_full_path())
