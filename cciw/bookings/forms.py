from django import forms

from cciw.bookings.models import BookingAccount
from cciw.cciwmain.forms import CciwFormMixin


class EmailForm(CciwFormMixin, forms.Form):
    email = forms.EmailField()


class AccountDetailsForm(CciwFormMixin, forms.ModelForm):
    class Meta:
        model = BookingAccount
        fields = [
            'name',
            'address',
            'post_code',
            'phone_number',
            'share_phone_number',
            ]

# Need to override these to fix various details for
# use by user
AccountDetailsForm.base_fields['name'].required = True
AccountDetailsForm.base_fields['address'].required = True
AccountDetailsForm.base_fields['post_code'].required = True
