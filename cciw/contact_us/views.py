import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core import mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import wordwrap
from django.template.response import TemplateResponse
from django.urls import reverse

from cciw.bookings.middleware import get_booking_account_from_request
from cciw.cciwmain.common import ajax_form_validate, get_current_domain
from cciw.contact_us.bogofilter import BogofilterStatus
from cciw.officers.views import cciw_secretary_or_booking_secretary_required

from .forms import AjaxContactUsForm, ContactUsForm
from .models import ContactType, Message

logger = logging.getLogger(__name__)

CONTACT_CHOICE_DESTS = {
    ContactType.BOOKINGFORM: settings.BOOKING_FORMS_EMAILS,
    ContactType.BOOKINGS: settings.BOOKING_SECRETARY_EMAILS,
    ContactType.GENERAL: settings.GENERAL_CONTACT_EMAILS,
    ContactType.WEBSITE: settings.WEBMASTER_EMAILS,
    ContactType.VOLUNTEERING: settings.VOLUNTEERING_EMAILS,
    ContactType.DATA_PROTECTION: settings.WEBMASTER_EMAILS,
}

for val in ContactType:
    assert val in CONTACT_CHOICE_DESTS, f"{val!r} missing form CONTACT_CHOICE_DESTS"


@ajax_form_validate(AjaxContactUsForm)
def contact_us(request):
    form_class = ContactUsForm
    booking_account = get_booking_account_from_request(request)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            to_emails = CONTACT_CHOICE_DESTS[form.cleaned_data["subject"]]
            if booking_account is not None and form.cleaned_data["email"] != booking_account.email:
                # They changed the email from the default, so disconnect
                # this message from the booking account, to avoid confusion
                booking_account = None
            msg: Message = form.save(commit=False)
            msg.booking_account = booking_account
            msg.save()
            status, score = msg.classify_with_bogofilter()
            if status == BogofilterStatus.SPAM and score > 0.95:
                logger.info("Not sending contact_us email id=%s with spam score %.3f", msg.id, score)
            else:
                send_contact_us_emails(to_emails, msg)
            return HttpResponseRedirect(reverse("cciw-contact_us-done"))
    else:
        initial = {}
        for val, caption in ContactType.choices:
            if val in request.GET:
                initial["subject"] = val
        if booking_account is not None:
            initial["email"] = booking_account.email
        form = form_class(initial=initial)

    return TemplateResponse(
        request,
        "cciw/contact_us.html",
        {
            "title": "Contact us",
            "form": form,
        },
    )


def contact_us_done(request):
    return TemplateResponse(
        request,
        "cciw/contact_us_done.html",
        {
            "title": "Contact us",
        },
    )


def send_contact_us_emails(to_emails, msg):
    # Since msg.message could contain arbitrary spam, we don't send
    # it in an email (to protect our email server's spam reputation).
    # Instead we send a link to a page that will show the message.

    body = f"""
A message has been sent on the CCiW website feedback form, follow
the link to view it:

{make_contact_us_view_url(msg)}

Spaminess: {msg.bogosity_percent}% - {msg.get_spam_classification_bogofilter_display().upper()}

"""

    email = mail.EmailMessage(
        subject=f"[CCIW] Website feedback {msg.id}",
        body=body,
        from_email=settings.SERVER_EMAIL,
        to=to_emails,
    )
    email.send()


@cciw_secretary_or_booking_secretary_required
@staff_member_required
def view_message(request, *, message_id: int):
    msg: Message = get_object_or_404(Message.objects.filter(id=int(message_id)))

    if request.method == "POST":
        if "mark_spam" in request.POST:
            msg.mark_spam()
            messages.info(request, "Marked as spam")
        elif "mark_ham" in request.POST:
            msg.mark_ham()
            messages.info(request, "Marked as ham")

    quoted_message_body = "\n".join(["> " + line for line in wordwrap(msg.message, 70).split("\n")])

    reply_template = """Dear {name},


----
On {created_at:%Y-%m-%d %H:%M}, {name} <{email}> wrote:

{quoted_message_body}
""".format(
        name=msg.name if msg.name else "user",
        created_at=msg.created_at,
        quoted_message_body=quoted_message_body,
        email=msg.email,
    )
    return TemplateResponse(
        request,
        "cciw/officers/view_contact_us_message.html",
        {
            "message": msg,
            "reply_template": reply_template,
            "subject": f"[CCIW] Contact form reply - message #{msg.id}",
            "is_popup": True,
        },
    )


def make_contact_us_view_url(msg):
    return "https://{domain}{path}".format(
        domain=get_current_domain(), path=reverse("cciw-contact_us-view", args=(msg.id,))
    )
