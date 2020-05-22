# -*- coding: utf-8 -*-
from django import forms
from django.utils.html import format_html

from cciw.bookings.models import Booking, BookingAccount, Price
from cciw.cciwmain import common
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain.models import Camp


class EmailForm(CciwFormMixin, forms.Form):
    email = forms.EmailField()


class AccountDetailsForm(CciwFormMixin, forms.ModelForm):

    class Meta:
        model = BookingAccount
        fields = [
            'name',
            'address_line1',
            'address_line2',
            'address_city',
            'address_county',
            'address_country',
            'address_post_code',
            'phone_number',
            'share_phone_number',
            'email_communication',
            'subscribe_to_mailings',
            'subscribe_to_newsletter',
        ]

    def save(self, *args, **kwargs):
        old_subscription = BookingAccount.objects.get(id=self.instance.id).subscribe_to_newsletter
        retval = super(AccountDetailsForm, self).save(*args, **kwargs)
        if old_subscription != self.instance.subscribe_to_newsletter:
            from cciw.bookings.mailchimp import update_newsletter_subscription
            update_newsletter_subscription(self.instance)
        return retval


# Need to override these to fix various details for use by user
for f in ['name', 'address_line1', 'address_city', 'address_country', 'address_post_code']:
    AccountDetailsForm.base_fields[f].required = True

AccountDetailsForm.base_fields['subscribe_to_mailings'].widget = forms.CheckboxInput()


class FixPriceMixin(object):
    """
    Changes the 'price_type' field to include prices from the current year.
    """
    def fix_price_choices(self):
        price_choices = self.fields['price_type'].choices
        year = common.get_thisyear()
        prices = dict((p.price_type, p.price) for p in Price.objects.filter(year=year))

        for i, (price_type, label) in enumerate(price_choices):
            if price_type in prices:
                caption = price_choices[i][1] + f" - £{prices[price_type]}"
                price_choices[i] = (price_choices[i][0], caption)
        self.fields['price_type'].choices = price_choices


class AddPlaceForm(FixPriceMixin, CciwFormMixin, forms.ModelForm):

    camp = forms.ChoiceField(choices=[],
                             widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super(AddPlaceForm, self).__init__(*args, **kwargs)

        def render_camp(c):
            availability_msg = (("Places available"
                                 if c.get_places_left()[0] > 0
                                 else "No places available!")
                                if c.is_open_for_bookings else "Closed for bookings")
            return format_html('<span class="with-camp-colors-{slug}">'
                               'Camp {name}'
                               '</span>'
                               ', {leaders}, {start_date}'
                               '<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
                               '<span class="placeAvailability">{availability}</span>',
                               url=c.get_absolute_url(),
                               slug=c.slug_name,
                               name=c.name,
                               leaders=c.leaders_formatted,
                               start_date=c.start_date.strftime("%e %b %Y"),
                               availability=availability_msg,
                               )
        self.fields['camp'].choices = [(c.id, render_camp(c))
                                       for c in Camp.objects.filter(year=common.get_thisyear())]
        self.fix_price_choices()

    class Meta:
        model = Booking
        fields = [
            'camp',
            'price_type',
            'first_name',
            'last_name',
            'sex',
            'date_of_birth',
            'address_line1',
            'address_line2',
            'address_city',
            'address_county',
            'address_country',
            'address_post_code',
            'phone_number',
            'email',
            'church',
            'contact_name',
            'contact_line1',
            'contact_line2',
            'contact_city',
            'contact_county',
            'contact_country',
            'contact_post_code',
            'contact_phone_number',
            'dietary_requirements',
            'gp_name',
            'gp_line1',
            'gp_line2',
            'gp_city',
            'gp_county',
            'gp_country',
            'gp_post_code',
            'gp_phone_number',
            'medical_card_number',
            'last_tetanus_injection',
            'allergies',
            'regular_medication_required',
            'illnesses',
            'can_swim_25m',
            'learning_difficulties',
            'serious_illness',
            'agreement'
        ]

    def clean_camp(self):
        camp_id = self.cleaned_data['camp']
        return Camp.objects.get(id=int(camp_id))


AddPlaceForm.base_fields['agreement'].required = True
AddPlaceForm.base_fields['date_of_birth'].widget.attrs['placeholder'] = 'YYYY-MM-DD'
AddPlaceForm.base_fields['date_of_birth'].help_text = '(YYYY-MM-DD)'
AddPlaceForm.base_fields['last_tetanus_injection'].widget.attrs['placeholder'] = 'YYYY-MM-DD'
AddPlaceForm.base_fields['last_tetanus_injection'].help_text = '(YYYY-MM-DD)'
