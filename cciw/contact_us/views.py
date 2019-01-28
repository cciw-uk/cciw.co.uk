from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core import mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import wordwrap
from django.urls import reverse

from cciw.bookings.views import ensure_booking_account_attr
from cciw.cciwmain.common import AjaxFormValidation, CciwBaseView, get_current_domain
from cciw.officers.views import cciw_secretary_or_booking_secretary_required

from .forms import (CONTACT_CHOICE_BOOKINGFORM, CONTACT_CHOICE_BOOKINGS, CONTACT_CHOICE_GENERAL, CONTACT_CHOICE_WEBSITE,
                    CONTACT_CHOICES, AjaxContactUsForm, ContactUsForm)
from .models import Message


class ContactUsBase(CciwBaseView):
    metadata_title = "Contact us"


class ContactUsFormView(AjaxFormValidation, ContactUsBase):
    form_class = ContactUsForm
    ajax_form_class = AjaxContactUsForm
    template_name = 'cciw/contact_us.html'

    def handle(self, request):
        ensure_booking_account_attr(request)
        # At module level, use of 'settings' seems to cause problems
        CONTACT_CHOICE_DESTS = {
            CONTACT_CHOICE_BOOKINGFORM: settings.BOOKING_FORMS_EMAILS,
            CONTACT_CHOICE_BOOKINGS: settings.BOOKING_SECRETARY_EMAILS,
            CONTACT_CHOICE_GENERAL: settings.GENERAL_CONTACT_EMAILS,
            CONTACT_CHOICE_WEBSITE: settings.WEBMASTER_EMAILS,
        }

        if request.method == "POST":
            form = self.form_class(request.POST)
            if form.is_valid():
                to_emails = CONTACT_CHOICE_DESTS[form.cleaned_data['subject']]
                booking_account = request.booking_account
                if booking_account is not None and form.cleaned_data['email'] != booking_account.email:
                    # They changed the email from the default, so disconnect
                    # this message from the booking account, to avoid confusion
                    booking_account = None
                msg = form.save(commit=False)
                msg.booking_account = booking_account
                msg.save()
                send_contact_us_emails(
                    to_emails,
                    msg)
                return HttpResponseRedirect(reverse('cciw-contact_us-done'))
        else:
            form = self.form_class(initial=self.get_initial(request))
        return self.render({'form': form})

    def get_initial(self, request):
        initial = {}
        for val, caption in CONTACT_CHOICES:
            if val in self.request.GET:
                initial['subject'] = val
        if request.booking_account is not None:
            initial['email'] = request.booking_account.email
        return initial


class ContactUsDone(ContactUsBase):
    template_name = 'cciw/contact_us_done.html'


def send_contact_us_emails(to_emails, msg):
    # Since msg.message could contain arbitrary spam, we don't send
    # it in an email (to protect our email server's spam reputation).
    # Instead we send a link to a page that will show the message.

    body = """
A message has been sent on the CCIW website feedback form, follow
the link to view it:

%(url)s

""" % dict(url=make_contact_us_view_url(msg))

    email = mail.EmailMessage(
        subject="[CCIW] Website feedback",
        body=body,
        from_email=settings.SERVER_EMAIL,
        to=to_emails,
    )
    email.send()


@cciw_secretary_or_booking_secretary_required
@staff_member_required
def view_message(request, message_id):
    msg = get_object_or_404(Message.objects.filter(id=int(message_id)))
    quoted_message_body = "\n".join(["> " + l for l in wordwrap(msg.message, 70).split("\n")])
    reply_template = """Dear {name},


----
On {timestamp}, <{email}> wrote:

{quoted_message_body}
""".format(name=msg.name if msg.name else "user",
           timestamp=msg.timestamp.strftime("%Y-%m-%d %H:%M"),
           quoted_message_body=quoted_message_body,
           email=msg.email)
    return render(request, 'cciw/officers/view_contact_us_message.html',
                  {
                      'message': msg,
                      'reply_template': reply_template,
                      'subject': '[CCIW] Contact form reply - message #{0}'.format(msg.id),
                      'is_popup': True,
                  })


def make_contact_us_view_url(msg):
    return 'https://%(domain)s%(path)s' % dict(
        domain=get_current_domain(),
        path=reverse('cciw-contact_us-view', args=(msg.id,)))


contact_us = ContactUsFormView.as_view()
contact_us_done = ContactUsDone.as_view()
