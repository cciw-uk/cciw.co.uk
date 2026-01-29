from typing import Any

from django.forms import Form, renderers
from django.utils.safestring import SafeString


class CciwFormMixin:
    """Form mixin that provides the rendering methods used on the CCiW site"""

    # Not used for the 'officers' section, which uses styling based on Django admin

    default_renderer = renderers.TemplatesSetting()
    template_name_p = "cciw/forms/p.html"
    template_name_p_formrow = "cciw/forms/p_formrow.html"
    required_css_class = "required"

    # Set to True in subclasses to use htmx validation.
    # Note that this will trigger `hx-preserve`
    # attributes, which is incompatible with some other
    # htmx usages where we want to overwrite form data
    # with HTML from the server.
    do_htmx_validation: bool = False

    # Dictionary from field name to label to override normal labels easily
    label_overrides: dict = {}

    def should_do_htmx_validation(self) -> bool:
        return self.do_htmx_validation

    def get_context(self, *args, **kwargs) -> dict[str, Any]:
        return super().get_context(*args, **kwargs) | {
            "formrow_template": self.template_name_p_formrow,
            "do_htmx_validation": self.should_do_htmx_validation(),
        }


def render_single_form_field(form: Form, field_name: str) -> SafeString:
    # Assumes form has CciwFormMixin as a base
    bound_field = form[field_name]
    label_text = form.label_overrides.get(field_name, None)
    return form.render(
        context={
            "field": bound_field,
            "errors": form.error_class(bound_field.errors, renderer=form.renderer),
            "do_htmx_validation": form.should_do_htmx_validation(),
        }
        | ({"label_tag": bound_field.label_tag(contents=label_text)} if label_text else {}),
        template_name=form.template_name_p_formrow,
    )
