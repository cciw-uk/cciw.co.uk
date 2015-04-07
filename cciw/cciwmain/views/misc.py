
from django import forms
from django.core import mail
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.text import wrap

from cciw.cciwmain.common import AjaxFormValidation, CciwBaseView
from cciw.cciwmain.forms import CciwFormMixin

def send_feedback(to_emails, from_email, name, message):
    message = wrap(message, 70)
    email = mail.EmailMessage(subject="CCIW website feedback",
                              body="""
The following message has been sent on the CCIW website feedback form:

From: %(name)s
Email: %(from_email)s
Message:
%(message)s

""" % locals(),
                              from_email=settings.SERVER_EMAIL,
                              to=to_emails,
                              headers={'Reply-To': from_email})
    email.send()

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

CONTACT_CHOICE_DESTS = {
    CONTACT_CHOICE_GENERAL: ['CONTACT_US_EMAIL'],
    CONTACT_CHOICE_BOOKINGFORM: ['BOOKING_FORM_EMAIL', 'CONTACT_US_EMAIL'],
    CONTACT_CHOICE_WEBSITE: ['WEBMASTER_EMAIL', 'CONTACT_US_EMAIL'],
    CONTACT_CHOICE_BOOKINGS: ['BOOKING_SECRETARY_EMAIL', 'CONTACT_US_EMAIL'],
}

class ContactUsForm(CciwFormMixin, forms.Form):
    subject = forms.ChoiceField(label="Subject", choices=CONTACT_CHOICES)
    email = forms.EmailField(label="Email address", max_length=320)
    name = forms.CharField(label="Name", max_length=200, required=False)
    message = forms.CharField(label="Message", widget=forms.Textarea)


class ContactUsBase(CciwBaseView):
    metadata_title = "Contact us"


class ContactUsFormView(AjaxFormValidation, ContactUsBase):
    form_class = ContactUsForm
    template_name = 'cciw/contact_us.html'

    def handle(self, request):
        if request.method == "POST":
            form = self.form_class(request.POST)
            if form.is_valid():
                to_emails = [getattr(settings, email) for email in CONTACT_CHOICE_DESTS[form.cleaned_data['subject']]]
                send_feedback(
                    to_emails,
                    form.cleaned_data['email'],
                    form.cleaned_data['name'],
                    form.cleaned_data['message']
                )
                return HttpResponseRedirect(reverse('cciwmain.misc.contact_us_done'))
        else:
            form = self.form_class(initial=self.get_initial())
        return self.render({'form': form})

    def get_initial(self):
        initial = {}
        for val, caption in CONTACT_CHOICES:
            if val in self.request.GET:
                initial['subject'] = val
        return initial


class ContactUsDone(ContactUsBase):
    template_name = 'cciw/contact_us_done.html'


contact_us = ContactUsFormView.as_view()
contact_us_done = ContactUsDone.as_view()

