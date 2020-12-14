from captcha.fields import CaptchaField
from django import forms

from cciw.cciwmain.forms import CciwFormMixin

from .models import Message

CONTACT_CHOICE_GENERAL = 'general'
CONTACT_CHOICE_WEBSITE = 'website'
CONTACT_CHOICE_BOOKINGS = 'bookings'
CONTACT_CHOICE_BOOKINGFORM = 'bookingform'

CONTACT_CHOICES = [
    (CONTACT_CHOICE_WEBSITE, 'Web site problems'),
    (CONTACT_CHOICE_BOOKINGFORM, 'Paper booking form request'),
    (CONTACT_CHOICE_BOOKINGS, 'Bookings'),
    (CONTACT_CHOICE_GENERAL, 'Other'),
]


class ContactUsForm(CciwFormMixin, forms.ModelForm):
    subject = forms.ChoiceField(label="Subject", choices=CONTACT_CHOICES)
    cx = CaptchaField(label="Captcha",
                      help_text="To show you are not a spam-bot please enter the text you see above")

    class Meta:
        model = Message
        fields = [
            'subject',
            'email',
            'name',
            'message',
            'cx',
        ]


class AjaxContactUsForm(ContactUsForm):
    class Meta:
        model = Message
        fields = [f for f in ContactUsForm.Meta.fields if f != "cx"]


# We have to remove the captcha field in AJAX validation
# because its clean() method removes the Captcha from the database
del AjaxContactUsForm.base_fields['cx']
