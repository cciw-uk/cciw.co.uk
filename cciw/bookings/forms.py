# -*- coding: utf-8 -*-
from django import forms
from django.forms.forms import BoundField
from django.utils.html import format_html

from cciw.bookings.models import Booking, BookingAccount, Price
from cciw.cciwmain import common
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain.models import Camp


class EmailForm(CciwFormMixin, forms.Form):
    email = forms.EmailField()


def migrate_address_form(*fields):
    """
    Creates a base class used to migrate data from old address field.
    """
    # If the old address is present, it should be displayed
    # in a non-editable box, with a message saying it needs to be migrated.
    # If it is not present, it should not be displayed at all.

    class MigrateAddressFormMixin(object):
        def __init__(self, data=None, instance=None, **kwargs):
            if data is not None and instance is not None:
                data = data.copy()
                # Disallow saving of data, by setting it from the instance
                # and ignoring what was posted.
                for f in fields:
                    data[f] = getattr(instance, f)
            super(MigrateAddressFormMixin, self).__init__(data=data, instance=instance, **kwargs)

        def render_field(self, name, field, top_errors, hidden_fields, label_text=None):
            if name in fields:
                has_data = False
                bf = BoundField(self, field, name)
                if bf.value():
                    has_data = True
                # We can have simplified logic relative to super.render_field,
                # since we don't need to worry about errors, required fields etc.
                field = (
                    "<div class=\"userError\">"
                    "We have been unable to automatically handle the following old address information. "
                    "Please split the information in this address into the fields below, "
                    "and ensure that the post code is correct:"
                    "</div>"
                ) + self.normal_row_template % {
                    'errors_html': '',
                    'label': bf.label_tag((label_text or bf.label) + ":"),
                    'field': bf.as_widget(attrs={'readonly': 'readonly'}),
                    'help_text': '',
                    'class': self.div_normal_class,
                    'divid': "div_id_%s" % bf.name,
                }
                hider = '' if has_data else 'style="display: none;"'
                return ('<div class="addressMigrationWrapper" {0}>{1}</div>'
                        .format(hider, field))
            else:
                return super(MigrateAddressFormMixin, self).render_field(name, field, top_errors,
                                                                         hidden_fields, label_text=label_text)

    return MigrateAddressFormMixin


class AccountDetailsForm(migrate_address_form('address'), CciwFormMixin, forms.ModelForm):

    class Meta:
        model = BookingAccount
        fields = [
            'name',
            'address',
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
                caption = price_choices[i][1] + " - £%s" % prices[price_type]
                price_choices[i] = (price_choices[i][0], caption)
        self.fields['price_type'].choices = price_choices


class AddPlaceForm(migrate_address_form('address', 'contact_address', 'gp_address'),
                   FixPriceMixin, CciwFormMixin, forms.ModelForm):

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
            'address',
            'address_line1',
            'address_line2',
            'address_city',
            'address_county',
            'address_country',
            'address_post_code',
            'phone_number',
            'email',
            'church',
            'contact_address',
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
            'gp_address',
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
