from django.db import models

from cciw.officers import formfields


class YyyyMmField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        kwargs['help_text'] = 'Enter the date in YYYY/MM format.'
        return super(YyyyMmField, self).__init__(*args, **kwargs)

    def formfield(self, *args, **kwargs):
        defaults = {'form_class': formfields.YyyyMmField}
        defaults.update(kwargs)
        return super(YyyyMmField, self).formfield(*args, **defaults)


class AddressField(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs['help_text'] = 'Full address, including post code and country'
        return super(AddressField, self).__init__(*args, **kwargs)


class ExplicitBooleanField(models.NullBooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['default'] = None
        super(ExplicitBooleanField, self).__init__(*args, **kwargs)

    def _has_changed(self, initial, data):
        # Sometimes data or initial could be None or '' which should be the
        # same thing as False.
        return bool(initial) != bool(data)


def required_field(field_class):
    """
    Required fields - the admin must be able to save them when empty,
    but need to mark as required if we are trying to finalise
    the object (e.g. save Application with 'complete' flag)

    So this returns a field class with options set appropiately --
    blank=True, but field.formfield() objects have '.required_field = True'
    which is checked later.
    """
    class NewDBField(field_class):
        def __init__(self, *args, **kwargs):
            kwargs['blank'] = True
            super(NewDBField, self).__init__(*args, **kwargs)

        def formfield(self, *args, **kwargs):
            f = super(NewDBField, self).formfield(*args, **kwargs)
            f.required_field = True
            return f

    NewDBField.__name__ = "Required" + field_class.__name__
    return NewDBField


# Need to be able to import these classes, as they become part of model definition
# which is stored in migrations.
RequiredCharField = required_field(models.CharField)
RequiredDateField = required_field(models.DateField)
RequiredEmailField = required_field(models.EmailField)
RequiredYyyyMmField = required_field(YyyyMmField)
RequiredTextField = required_field(models.TextField)
RequiredExplicitBooleanField = required_field(ExplicitBooleanField)
RequiredAddressField = required_field(AddressField)
