from django.forms import renderers


class CciwFormMixin:
    """Form mixin that provides the rendering methods used on the CCiW site"""

    default_renderer = renderers.TemplatesSetting()
    template_name_p = "cciw/forms/p.html"
    template_name_p_formrow = "cciw/forms/p_formrow.html"
    error_css_class = "validationErrors"
    required_css_class = "required"

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {"formrow_template": self.template_name_p_formrow}

    # TODO fixup standardform* functions or replace with HTMX
