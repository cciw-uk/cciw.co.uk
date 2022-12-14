from django.db import models

from cciw.officers import formfields


class YyyyMmField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 7
        kwargs["help_text"] = "Enter the date in YYYY/MM format."
        super().__init__(*args, **kwargs)

    def formfield(self, *args, **kwargs):
        defaults = {"form_class": formfields.YyyyMmField}
        defaults.update(kwargs)
        return super().formfield(*args, **defaults)


class AddressField(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs["help_text"] = "Full address, including post code and country"
        super().__init__(*args, **kwargs)


class ExplicitBooleanField(models.BooleanField):
    def __init__(self, *args, **kwargs):
        kwargs["default"] = None
        kwargs["null"] = True
        super().__init__(*args, **kwargs)


def required_field(field_class):
    """
    Required fields - the admin must be able to save them when empty,
    but need to mark as required if we are trying to finalise
    the object (e.g. save Application with 'complete' flag)

    So this returns a field class with options set appropiately --
    blank=True, but field.formfield() objects have '.required_field = True'
    which is checked later.
    """

    name = "Required" + field_class.__name__

    class NewDBField(field_class):
        def __init__(self, *args, **kwargs):
            kwargs["blank"] = True
            super().__init__(*args, **kwargs)

        def formfield(self, *args, **kwargs):
            f = super().formfield(*args, **kwargs)
            f.required_field = True
            return f

        def deconstruct(self):
            attname, field_path, posargs, kwargs = super().deconstruct()
            # Django 2.2 gets field_path wrong for some reason
            field_path = "cciw.officers.fields." + name
            return attname, field_path, posargs, kwargs

    NewDBField.__name__ = name
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
