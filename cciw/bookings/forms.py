from django import forms

from cciw.cciwmain.forms import CciwFormMixin

class EmailForm(CciwFormMixin, forms.Form):
    email = forms.EmailField()

