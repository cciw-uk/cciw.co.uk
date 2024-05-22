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
            "name",
            "address_line1",
            "address_line2",
            "address_city",
            "address_county",
            "address_country",
            "address_post_code",
            "phone_number",
            "share_phone_number",
            "email_communication",
            "subscribe_to_mailings",
            "subscribe_to_newsletter",
        ]

    do_htmx_validation = True

    def save(self, *args, **kwargs):
        old_subscription = BookingAccount.objects.get(id=self.instance.id).subscribe_to_newsletter
        retval = super().save(*args, **kwargs)
        if old_subscription != self.instance.subscribe_to_newsletter:
            from cciw.bookings.mailchimp import update_newsletter_subscription

            update_newsletter_subscription(self.instance)
        return retval


# Need to override these to fix various details for use by user
for f in ["name", "address_line1", "address_city", "address_country", "address_post_code"]:
    AccountDetailsForm.base_fields[f].required = True

AccountDetailsForm.base_fields["subscribe_to_mailings"].widget = forms.CheckboxInput()


class FixPriceMixin:
    """
    Changes the 'price_type' field to include prices from the current year.
    """

    def fix_price_choices(self):
        price_choices = self.fields["price_type"].choices
        year = common.get_thisyear()
        prices = {p.price_type: p.price for p in Price.objects.filter(year=year)}

        price_choices_2 = []
        for i, (price_type, label) in enumerate(price_choices):
            if price_type in prices:
                caption = label + f" - £{prices[price_type]}"
                price_choices_2.append((price_type, caption))
            else:
                price_choices_2.append((price_type, label))
        self.fields["price_type"].choices = price_choices_2


class AddPlaceForm(FixPriceMixin, CciwFormMixin, forms.ModelForm):
    camp = forms.ChoiceField(choices=[], widget=forms.RadioSelect)

    do_htmx_validation = True

    label_overrides = {
        "camp": "Choose camp:",
        "price_type": "Price",
        "first_name": "First name",
        "last_name": "Surname",
        "church": "Name of church (if any)",
        "contact_name": "Name",
        "contact_phone_number": "Phone number",
        "gp_name": "Name",
        "gp_phone_number": "Phone number",
        "last_tetanus_injection_date": "Last tetanus injection (if known)",
        "allergies": "Allergies (including medication)",
        "illnesses": "Medical conditions (e.g. asthma, epilepsy, diabetes)",
        "learning_difficulties": "Anything else we need to be aware of in relation to attending camp, including learning/behavioural difficulties, being registered with social care?",
        "serious_illness": "Serious condition/illness",
        "agreement": "Agree to above conditions",
        "publicity_photos_agreement": "Agree to photos being taken and used for publicity.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def render_camp(c):
            availability_msg = (
                ("Places available" if c.get_places_left().total > 0 else "No places available!")
                if c.is_open_for_bookings
                else "Closed for bookings"
            )
            return format_html(
                '<span class="with-camp-colors-{slug}">'
                "Camp {name}"
                "</span>"
                ", {leaders}, {start_date}"
                "<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                '<span class="placeAvailability">{availability}</span>',
                url=c.get_absolute_url(),
                slug=c.slug_name,
                name=c.name,
                leaders=c.leaders_formatted,
                start_date=c.start_date.strftime("%e %b %Y"),
                availability=availability_msg,
            )

        self.fields["camp"].choices = [(c.id, render_camp(c)) for c in Camp.objects.filter(year=common.get_thisyear())]
        self.fix_price_choices()

    class Meta:
        model = Booking
        fields = [
            "camp",
            "price_type",
            "first_name",
            "last_name",
            "sex",
            "birth_date",
            "address_line1",
            "address_line2",
            "address_city",
            "address_county",
            "address_country",
            "address_post_code",
            "phone_number",
            "email",
            "church",
            "contact_name",
            "contact_line1",
            "contact_line2",
            "contact_city",
            "contact_county",
            "contact_country",
            "contact_post_code",
            "contact_phone_number",
            "dietary_requirements",
            "gp_name",
            "gp_line1",
            "gp_line2",
            "gp_city",
            "gp_county",
            "gp_country",
            "gp_post_code",
            "gp_phone_number",
            "medical_card_number",
            "last_tetanus_injection_date",
            "allergies",
            "regular_medication_required",
            "illnesses",
            "can_swim_25m",
            "learning_difficulties",
            "serious_illness",
            "agreement",
            "publicity_photos_agreement",
        ]

    def clean_camp(self):
        camp_id = self.cleaned_data["camp"]
        return Camp.objects.get(id=int(camp_id))


AddPlaceForm.base_fields["agreement"].required = True
for f in ["birth_date", "last_tetanus_injection_date"]:
    AddPlaceForm.base_fields[f].widget.attrs["placeholder"] = "YYYY-MM-DD"
    AddPlaceForm.base_fields[f].widget.format = "%Y-%m-%d"

for f in [
    "dietary_requirements",
    "church",
    "allergies",
    "regular_medication_required",
    "illnesses",
    "learning_difficulties",
]:
    AddPlaceForm.base_fields[f].widget.attrs["placeholder"] = "Leave empty if none or N/A"


class UsePreviousData(CciwFormMixin, forms.Form):
    copy_from_booking = forms.ChoiceField(required=True, label="Copy from")
    copy_camper_details = forms.BooleanField(required=False, label="Copy camper details (name + medical)")
    copy_address_details = forms.BooleanField(required=False, label="Copy camper address")
    copy_contact_address_details = forms.BooleanField(required=False, label="Copy contact address")
    copy_gp_details = forms.BooleanField(label="Copy GP information", required=False)

    def __init__(self, *args, previous_bookings=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["copy_from_booking"].choices = [
            (
                b.id,
                f"{b.first_name} {b.last_name} {b.created_at.year}; Post code: {b.address_post_code}; GP: {b.gp_name}",
            )
            for b in previous_bookings
        ]
