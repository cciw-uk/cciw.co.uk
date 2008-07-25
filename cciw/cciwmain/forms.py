from django.utils.html import escape
from django.forms.forms import BoundField
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

class CciwFormMixin(object):
    """Form mixin that provides the rendering methods used on the CCIW site"""
    def as_p(self):
        "Returns this form rendered as HTML <p>s."

        ## Remember to change cciwutils.js standardform_ functions if the
        ## HTML here is changed
        normal_row = '<div id="%(divid)s" class="%(class)s">%(label)s %(field)s%(help_text)s</div>'
        error_row = u'<div class="validationErrorTop">%s</div>'
        help_text_html = u' %s'
        normal_class = u'formrow'
        error_class = u'formrow validationErrorBottom'
        start = u'<div class="form">'
        end = u'</div>'
        required_text = u' <a href="#" title="This field is required">*</a>'
        
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []
        output.append(start)
        for name, field in self.fields.items():
            bf = BoundField(self, field, name)
            bf_errors = self.error_class([escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend([u'(Hidden field %s) %s' % (name, force_unicode(e)) for e in bf_errors])
                hidden_fields.append(unicode(bf))
            else:
                if bf_errors:
                    output.append(error_row % force_unicode(bf_errors))
                    cssclass = error_class
                else:
                    cssclass = normal_class
                if bf.label:
                    label = escape(force_unicode(bf.label))
                    # Only add the suffix if the label does not end in
                    # punctuation.
                    if self.label_suffix:
                        if label[-1] not in ':?.!':
                            label += self.label_suffix
                    if field.required:
                        label += required_text
                        label_attrs = {'class':'required'}
                    else:
                        label_attrs = {}
                    label = bf.label_tag(label, attrs=label_attrs) or ''
                else:
                    label = ''
                if field.help_text:
                    help_text = help_text_html % force_unicode(field.help_text)
                else:
                    help_text = u''
                output.append(normal_row % {
                        'errors': force_unicode(bf_errors), 
                        'label': force_unicode(label), 
                        'field': unicode(bf), 
                        'help_text': help_text,
                        'class': cssclass,
                        'divid': "div_id_%s" % bf.name
                        })
        if top_errors:
            output.insert(0, error_row % top_errors)
        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = u''.join(hidden_fields)
            output.append(str_hidden)
        output.append(end)
        return mark_safe(u'\n'.join(output))
