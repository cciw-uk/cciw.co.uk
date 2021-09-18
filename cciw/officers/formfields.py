import re

from django import forms

yyyy_mm_re = re.compile(r'^\d{4}/\d{2}$')


class YyyyMmField(forms.CharField):
    """
    Form field class that validates its input to be in the form
    YYYY/MM
    """

    def clean(self, value):
        if not self.required and (value == "" or value is None):
            return ""
        if not yyyy_mm_re.match(value):
            raise forms.ValidationError("This field must be in the form YYYY/MM.")
        return value
