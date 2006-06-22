import os

from django import forms
from django import shortcuts
from django import template
from django.core import mail
from django.conf import settings
from django.utils.text import wrap

from cciw.cciwmain.common import standard_extra_context, get_thisyear

def send_feedback(email, name, message):
    message = wrap(message, 70)
    mail.send_mail("CCIW website feedback", """
The following message has been sent on the CCIW website feedback form:

From: %(name)s
Email: %(email)s
Message:
%(message)s

""" % locals(), "website@cciw.co.uk", [settings.FEEDBACK_EMAIL_TO])
    

class FeedbackManipulator(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.EmailField(field_name="email", length=30, maxlength=200, is_required=True),
            forms.TextField(field_name="name", length=30, maxlength=200),
            forms.LargeTextField(field_name="message", is_required=True),
        )

def feedback(request):
    c = standard_extra_context(title="Contact us")
    
    manipulator = FeedbackManipulator()
    
    if request.POST:
        new_data = request.POST.copy()
        errors = manipulator.get_validation_errors(new_data)
        
        if not errors:
            manipulator.do_html2python(new_data)
            send_feedback(new_data['email'], new_data['name'], new_data['message'])
            c['message'] = "Thank you, your message has been sent."
    else:
        errors = new_data = {}
    
    form = forms.FormWrapper(manipulator, new_data, errors)
    c['form'] = form
    c['errors'] = errors
    return shortcuts.render_to_response('cciw/feedback.html', 
                context_instance=template.RequestContext(request, c))

def bookingform(request):
    """
    Displays a page with a download link for the booking form 
    if it is available.
    """
    c = standard_extra_context(title="Booking form")
    year = get_thisyear()
    bookingform_relpath = "%s/booking_form_%s.pdf" % (settings.BOOKINGFORMDIR, year)
    if os.path.isfile("%s%s" % (settings.MEDIA_ROOT, bookingform_relpath )):
        c['bookingform'] = bookingform_relpath
    return shortcuts.render_to_response('cciw/booking.html',
        context_instance=template.RequestContext(request, c))
