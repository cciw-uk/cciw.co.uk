from django import forms

from cciw.bookings.models import BookingAccount, Booking
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain.common import get_thisyear


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

# Need to override these to fix various details for use by user
AccountDetailsForm.base_fields['name'].required = True
AccountDetailsForm.base_fields['address'].required = True
AccountDetailsForm.base_fields['post_code'].required = True


class AddPlaceForm(CciwFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'camp',
            'price_type',
            'name',
            'sex',
            'date_of_birth',
            'address',
            'post_code',
            'phone_number',
            'email',
            'church',
            'south_wales_transport',
            'contact_name',
            'contact_phone_number',
            'dietary_requirements',
            'gp_name',
            'gp_address',
            'gp_phone_number',
            'medical_card_number',
            'last_tetanus_injection',
            'allergies',
            'regular_medication_required',
            'illnesses',
            'learning_difficulties',
            'serious_illness',
            'agreement'
            ]

    def clean_camp(self):
        camp = self.cleaned_data['camp']
        thisyear = get_thisyear()
        if camp.year != thisyear:
            raise forms.ValidationError('Only a camp in %s can be selected.' % thisyear)

        return camp

AddPlaceForm.base_fields['agreement'].required = True
