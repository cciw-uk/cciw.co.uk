# -*- coding: utf-8 -*-
from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe

from cciw.bookings.models import BookingAccount, Booking, Price
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp


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

    camp = forms.ChoiceField(choices=[],
                             widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super(AddPlaceForm, self).__init__(*args, **kwargs)
        def render_camp(c):
            return (escape("Camp %d, %s, %s" % (c.number, c.leaders_formatted,
                                                c.start_date.strftime("%e %b %Y"))) +
                    '<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' +
                    '<span class="placeAvailability">' +
                    escape("(Places left: %d total, max %d for boys, max %d for girls)" %
                           c.get_places_left()) + '</span>')
        self.fields['camp'].choices = [(c.id, mark_safe(render_camp(c)))
                                       for c in Camp.objects.filter(year=get_thisyear())]
        price_choices = self.fields['price_type'].choices
        prices = dict((p.price_type, p.price) for p in Price.objects.filter(year=get_thisyear()))

        for i, (price_type, label) in enumerate(price_choices):
            if price_type in prices:
                price_choices[i] = (price_choices[i][0], price_choices[i][1] + " - £%s" % prices[price_type])
        self.fields['price_type'].choices = price_choices


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
        camp_id = self.cleaned_data['camp']
        return Camp.objects.get(id=int(camp_id))

AddPlaceForm.base_fields['agreement'].required = True
