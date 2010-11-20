import os

from django import forms
from django import shortcuts
from django import template
from django.core import mail
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.text import wrap
from django.views.generic.base import TemplateView

from cciw.cciwmain.common import standard_extra_context, get_thisyear, JsonFormView, DefaultMetaData
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain import utils

def send_feedback(email, name, message):
    message = wrap(message, 70)
    mail.send_mail("CCIW website feedback", """
The following message has been sent on the CCIW website feedback form:

From: %(name)s
Email: %(email)s
Message:
%(message)s

""" % locals(), "website@cciw.co.uk", [settings.FEEDBACK_EMAIL_TO])

class FeedbackForm(CciwFormMixin, forms.Form):
    email = forms.EmailField(label="Email address", max_length=320)
    name = forms.CharField(label="Name", max_length=200, required=False)
    message = forms.CharField(label="Message", widget=forms.Textarea)

class FeedbackBase(DefaultMetaData):
    metadata_title = u"Contact us"

class FeedbackFormView(FeedbackBase, JsonFormView):
    form_class = FeedbackForm
    template_name = 'cciw/feedback.html'

    def get_success_url(self):
        return reverse('cciwmain.misc.feedback_done')

    def form_valid(self, form):
        send_feedback(form.cleaned_data['email'], form.cleaned_data['name'],
                      form.cleaned_data['message'])
        return super(FeedbackFormView, self).form_valid(form)

class FeedbackDone(FeedbackBase, TemplateView):
    template_name = 'cciw/feedback_done.html'

feedback = FeedbackFormView.as_view()
feedback_done = FeedbackDone.as_view()

def bookingform(request):
    """
    Displays a page with a download link for the booking form
    if it is available.
    """
    c = standard_extra_context(title="Booking form")
    year = get_thisyear()
    bookingform_relpath = "%s/booking_form_%s.pdf" % (settings.BOOKINGFORMDIR, year)
    if os.path.isfile("%s/%s" % (settings.MEDIA_ROOT, bookingform_relpath)):
        c['bookingform'] = bookingform_relpath
    return shortcuts.render_to_response('cciw/booking.html',
        context_instance=template.RequestContext(request, c))
