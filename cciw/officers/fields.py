from django.db import models
import cciw.middleware.threadlocals as threadlocals
from cciw.officers import formfields


class YyyyMmField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        kwargs['help_text'] = u'Enter the date in YYYY/MM format.'
        return super(YyyyMmField, self).__init__(*args, **kwargs)

    def formfield(self, *args, **kwargs):
        defaults = {'form_class': formfields.YyyyMmField}
        defaults.update(kwargs)
        return super(YyyyMmField, self).formfield(*args, **defaults)


class AddressField(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs['help_text'] = u'Full address, including post code and country'
        return  super(AddressField, self).__init__(*args, **kwargs)


class ExplicitBooleanField(models.NullBooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['default'] = None
        super(ExplicitBooleanField, self).__init__(*args, **kwargs)


def required_field(field_class, *args, **kwargs):
    """
    Returns a field with options set appropiately for "required fields" --
    field.formfield() objects have '.required_field = True'.
    """
    kwargs['blank'] = True
    class NewDBField(field_class):
        def formfield(self, *args, **kwargs):
            f = super(NewDBField, self).formfield(*args, **kwargs)
            f.required_field = True
            return f

    if not threadlocals.is_web_request():
        # Allow South to find it by giving it a unique name and putting it in
        # this module.
        import sys
        NewDBField.__name__ = "Required" + field_class.__name__
        sys.modules['cciw.officers.fields'].__dict__[NewDBField.__name__] = NewDBField

    return NewDBField(*args, **kwargs)


if not threadlocals.is_web_request():
    # Allow South to introspect these - they are all based on builtin fields.
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^cciw\.officers\.fields\.Required*"])
    add_introspection_rules([], ["^cciw\.officers\.fields\.YyyyMmField"])
    add_introspection_rules([], ["^cciw\.officers\.fields\.AddressField"])

    # Could probably have done this using an introspection rule, but for
    # compatiblity with how we started we must do it this way.
    ExplicitBooleanField = models.NullBooleanField
