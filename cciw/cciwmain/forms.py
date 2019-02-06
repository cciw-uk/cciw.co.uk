from django.forms.forms import BoundField
from django.utils.encoding import force_text
from django.utils.html import escape, mark_safe


class CciwFormMixin(object):
    """Form mixin that provides the rendering methods used on the CCiW site"""

    normal_row_template = \
        '<div id="%(divid)s" class="%(class)s">%(errors_html)s' + \
        '<div class="field">%(label)s %(field)s%(help_text)s</div></div>'
    error_row_template = '<div class="userError">%s</div>'
    errors_template = '<div class="fieldMessages">%s</div>'

    help_text_html_template = ' <span class="field-help">%s</span>'

    div_normal_class = 'formrow'
    div_error_class = 'formrow validationErrors'

    start_template = '<div class="form">'
    end_template = '</div>'

    def as_p(self):
        "Returns this form rendered as HTML <p>s."

        # Remember to change cciwutils.js standardform_ functions if the HTML
        # here is changed
        top_errors = self.non_field_errors()  # Errors that should be displayed above all fields.
        output, hidden_fields = [], []
        output.append(self.start_template)
        for name, field in self.fields.items():
            output.append(self.render_field(name, field, top_errors, hidden_fields))
        if top_errors:
            output.insert(0, self.error_row_template % top_errors)
        if hidden_fields:  # Insert any hidden fields in the last row.
            str_hidden = ''.join(hidden_fields)
            output.append(str_hidden)
        output.append(self.end_template)
        return mark_safe('\n'.join(output))

    def render_field(self, name, field, top_errors, hidden_fields, label_text=None):
        output = []
        bf = BoundField(self, field, name)
        bf_errors = self.error_class([escape(error) for error in bf.errors])  # Escape and cache in local variable.
        if bf.is_hidden:
            if bf_errors:
                top_errors.extend(['(Hidden field %s) %s' % (name, force_text(e)) for e in bf_errors])
            hidden_fields.append(str(bf))
        else:
            if bf_errors:
                errors_html = self.errors_template % force_text(bf_errors)
                cssclass = self.div_error_class
            else:
                errors_html = ''
                cssclass = self.div_normal_class
            if label_text is None and bf.label:
                label_text = escape(force_text(bf.label))
            if label_text is not None:
                # Only add the suffix if the label does not end in
                # punctuation.
                if self.label_suffix:
                    if label_text[-1] not in ':?.!':
                        label_text += self.label_suffix
                if field.required:
                    label_attrs = {'class': 'required'}
                else:
                    label_attrs = {}
                label = bf.label_tag(label_text, attrs=label_attrs) or ''
            else:
                label = ''
            if field.help_text:
                help_text = self.help_text_html_template % force_text(field.help_text)
            else:
                help_text = ''
            output.append(self.normal_row_template % {
                'errors_html': errors_html,
                'label': force_text(label),
                'field': str(bf),
                'help_text': help_text,
                'class': cssclass,
                'divid': "div_id_%s" % bf.name
            })

            return ''.join(output)
