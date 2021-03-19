from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core import mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import wordwrap
from django.template.response import TemplateResponse
from django.urls import reverse

from cciw.bookings.views import ensure_booking_account_attr
from cciw.cciwmain.common import ajax_form_validate, get_current_domain
from cciw.officers.views import cciw_secretary_or_booking_secretary_required

from .forms import AjaxContactUsForm, ContactType, ContactUsForm
from .models import Message

CONTACT_CHOICE_DESTS = {
    ContactType.BOOKINGFORM: settings.BOOKING_FORMS_EMAILS,
    ContactType.BOOKINGS: settings.BOOKING_SECRETARY_EMAILS,
    ContactType.GENERAL: settings.GENERAL_CONTACT_EMAILS,
    ContactType.WEBSITE: settings.WEBMASTER_EMAILS,
}

for val in ContactType:
    assert val in CONTACT_CHOICE_DESTS, f"{val!r} missing form CONTACT_CHOICE_DESTS"


@ajax_form_validate(AjaxContactUsForm)
def contact_us(request):
    form_class = ContactUsForm
    ensure_booking_account_attr(request)
    # At module level, use of 'settings' seems to cause problems

    if request.method == "POST":
        form = form_class(request.POST)
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
        initial = {}
        for val, caption in ContactType.choices:
            if val in request.GET:
                initial['subject'] = val
        if request.booking_account is not None:
            initial['email'] = request.booking_account.email
        form = form_class(initial=initial)

    return TemplateResponse(request, 'cciw/contact_us.html', {
        'title': 'Contact us',
        'form': form,
    })


def contact_us_done(request):
    return TemplateResponse(request, 'cciw/contact_us_done.html', {
        'title': 'Contact us',
    })


def send_contact_us_emails(to_emails, msg):
    # Since msg.message could contain arbitrary spam, we don't send
    # it in an email (to protect our email server's spam reputation).
    # Instead we send a link to a page that will show the message.

    body = f"""
A message has been sent on the CCiW website feedback form, follow
the link to view it:

{make_contact_us_view_url(msg)}

"""

    email = mail.EmailMessage(
        subject="[CCIW] Website feedback",
        body=body,
        from_email=settings.SERVER_EMAIL,
        to=to_emails,
    )
    email.send()


@cciw_secretary_or_booking_secretary_required
@staff_member_required
def view_message(request, *, message_id: int):
    msg = get_object_or_404(Message.objects.filter(id=int(message_id)))
    quoted_message_body = "\n".join(["> " + line for line in wordwrap(msg.message, 70).split("\n")])
    reply_template = """Dear {name},


----
On {timestamp:%Y-%m-%d %H:%M}, {name} <{email}> wrote:

{quoted_message_body}
""".format(name=msg.name if msg.name else "user",
           timestamp=msg.timestamp,
           quoted_message_body=quoted_message_body,
           email=msg.email)
    return TemplateResponse(request, 'cciw/officers/view_contact_us_message.html', {
        'message': msg,
        'reply_template': reply_template,
        'subject': f'[CCIW] Contact form reply - message #{msg.id}',
        'is_popup': True,
    })


def make_contact_us_view_url(msg):
    return 'https://{domain}{path}'.format(
        domain=get_current_domain(),
        path=reverse('cciw-contact_us-view', args=(msg.id,)))
