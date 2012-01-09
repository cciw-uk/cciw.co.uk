import os

from django import forms
from django.core import mail
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.text import wrap
from django.views.generic.base import TemplateView

from cciw.cciwmain.common import get_thisyear, AjaxyFormView, DefaultMetaData
from cciw.cciwmain.forms import CciwFormMixin

def send_feedback(to_emails, from_email, name, message):
    message = wrap(message, 70)
    mail.send_mail("CCIW website feedback", """
The following message has been sent on the CCIW website feedback form:

From: %(name)s
Email: %(from_email)s
Message:
%(message)s

""" % locals(), settings.SERVER_EMAIL, to_emails)

CONTACT_CHOICE_GENERAL = 'general'
CONTACT_CHOICE_WEBSITE = 'website'
CONTACT_CHOICE_BOOKINGS = 'bookings'
CONTACT_CHOICE_BOOKINGFORM = 'bookingform'

CONTACT_CHOICES = [
    (CONTACT_CHOICE_WEBSITE, 'Web site problems'),
    (CONTACT_CHOICE_BOOKINGFORM, 'Booking form request'),
    (CONTACT_CHOICE_BOOKINGS, 'Bookings'),
    (CONTACT_CHOICE_GENERAL, 'Other'),
]

CONTACT_CHOICE_DESTS = {
    CONTACT_CHOICE_GENERAL: ['FEEDBACK_EMAIL'],
    CONTACT_CHOICE_BOOKINGFORM: ['BOOKING_FORM_EMAIL', 'FEEDBACK_EMAIL'],
    CONTACT_CHOICE_WEBSITE: ['WEBMASTER_EMAIL', 'FEEDBACK_EMAIL'],
    CONTACT_CHOICE_BOOKINGS: ['BOOKING_SECRETARY_EMAIL', 'FEEDBACK_EMAIL'],
}

class FeedbackForm(CciwFormMixin, forms.Form):
    subject = forms.ChoiceField(label="Subject", choices=CONTACT_CHOICES)
    email = forms.EmailField(label="Email address", max_length=320)
    name = forms.CharField(label="Name", max_length=200, required=False)
    message = forms.CharField(label="Message", widget=forms.Textarea)

class FeedbackBase(DefaultMetaData):
    metadata_title = u"Contact us"

class FeedbackFormView(FeedbackBase, AjaxyFormView):
    form_class = FeedbackForm
    template_name = 'cciw/feedback.html'

    def get_initial(self):
        initial = {}
        for val, caption in CONTACT_CHOICES:
            if val in self.request.GET:
                initial['subject'] = val
        return initial

    def get_success_url(self):
        return reverse('cciwmain.misc.feedback_done')

    def form_valid(self, form):
        to_emails = [getattr(settings, email) for email in CONTACT_CHOICE_DESTS[form.cleaned_data['subject']]]
        send_feedback(to_emails,
                      form.cleaned_data['email'],
                      form.cleaned_data['name'],
                      form.cleaned_data['message'])
        return super(FeedbackFormView, self).form_valid(form)

class FeedbackDone(FeedbackBase, TemplateView):
    template_name = 'cciw/feedback_done.html'

feedback = FeedbackFormView.as_view()
feedback_done = FeedbackDone.as_view()

