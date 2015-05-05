from django import template


def cciw_form_field(form, field_name, label):
    """
    Display a single field in the standard CCIW format.
    """
    # Assumes form has CciwFormMixin as a base

    top_errors, hidden_fields = [], []  # these will be discarded.
    return (form.start_template +
            form.render_field(field_name, form.fields[field_name],
                              top_errors, hidden_fields, label_text=label) +
            form.end_template)


register = template.Library()
register.simple_tag(cciw_form_field)
