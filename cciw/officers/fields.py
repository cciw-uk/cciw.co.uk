import re
from django.db import models
import cciw.middleware.threadlocals as threadlocals

yyyy_mm_re = re.compile('^\d{4}/\d{2}$')

def yyyy_mm_validator(field_data, all_data):
    if not yyyy_mm_re.match(field_data):
        raise ValidationError("This field must be in the form YYYY/MM.")

class YyyyMmField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        validators = list(kwargs.get('validator_list', ()))
        validators.append(yyyy_mm_validator)
        kwargs['validator_list'] = validators
        kwargs['help_text'] = u'Enter the date in YYYY/MM format.'
        return super(YyyyMmField, self).__init__(*args, **kwargs)

class AddressField(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs['help_text'] = u'Full address, including post code and country'
        return  super(AddressField, self).__init__(*args, **kwargs)

class ExplicitBooleanField(models.NullBooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['default'] = None
        super(ExplicitBooleanField, self).__init__(*args, **kwargs)

if not threadlocals.is_web_request():
    # When installing, we need the following line.  It is only
    # executed in the command line context.
    ExplicitBooleanField = models.NullBooleanField

def required_field(field_class, *args, **kwargs):
    """Returns a field with options set appropiately
    for "required fields" -- field.formfield() objects
    have '.required_field = True'."""
    kwargs['blank'] = True
    class NewDBField(field_class):
        def formfield(self, *args, **kwargs):
            f = super(field_class, self).formfield(*args, **kwargs)
            f.required_field = True
            return f
    return NewDBField(*args, **kwargs)
