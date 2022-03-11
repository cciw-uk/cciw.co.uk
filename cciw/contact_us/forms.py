from captcha.fields import CaptchaField
from django import forms
from django.db.models import TextChoices

from cciw.cciwmain.forms import CciwFormMixin

from .models import Message


class ContactType(TextChoices):
    WEBSITE = "website", "Web site problems"
    BOOKINGFORM = "bookingform", "Paper booking form request"
    BOOKINGS = "bookings", "Bookings"
    DATA_PROTECTION = "data_protection", "Data protection and related"
    VOLUNTEERING = "volunteering", "Volunteering"
    GENERAL = "general", "Other"


class ContactUsForm(CciwFormMixin, forms.ModelForm):
    subject = forms.ChoiceField(label="Subject", choices=ContactType.choices)
    cx = CaptchaField(label="Captcha", help_text="To show you are not a spam-bot please enter the text you see above")

    class Meta:
        model = Message
        fields = [
            "subject",
            "email",
            "name",
            "message",
            "cx",
        ]


class AjaxContactUsForm(ContactUsForm):
    class Meta:
        model = Message
        fields = [f for f in ContactUsForm.Meta.fields if f != "cx"]


# We have to remove the captcha field in AJAX validation
# because its clean() method removes the Captcha from the database
del AjaxContactUsForm.base_fields["cx"]
