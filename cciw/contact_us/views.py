import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import wordwrap
from django.template.response import TemplateResponse
from django.urls import reverse

from cciw.bookings.middleware import get_booking_account_from_request
from cciw.cciwmain.common import htmx_form_validate
from cciw.officers.views.utils.auth import cciw_secretary_or_booking_secretary_required

from .forms import ContactUsForm, ReclassifyForm, ValidationContactUsForm
from .models import ContactType, Message

logger = logging.getLogger(__name__)


@htmx_form_validate(form_class=ValidationContactUsForm)
def contact_us(request):
    form_class = ContactUsForm
    booking_account = get_booking_account_from_request(request)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            if booking_account is not None and form.cleaned_data["email"] != booking_account.email:
                # They changed the email from the default, so disconnect
                # this message from the booking account, to avoid confusion
                booking_account = None
            msg: Message = form.save(commit=False)
            msg.booking_account = booking_account
            msg.save()
            msg.classify_with_bogofilter()
            msg.send_emails()
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


@cciw_secretary_or_booking_secretary_required
@staff_member_required
def view_message(request, *, message_id: int):
    msg: Message = get_object_or_404(Message.objects.filter(id=int(message_id)))

    reclassify_form = None
    if request.method == "POST":
        if "mark_spam" in request.POST:
            msg.mark_spam()
            messages.info(request, "Marked as spam")
        elif "mark_ham" in request.POST:
            msg.mark_ham()
            messages.info(request, "Marked as ham")
        elif "reclassify" in request.POST:
            reclassify_form = ReclassifyForm(request.POST, instance=msg)
            if reclassify_form.is_valid():
                msg = reclassify_form.save()
                msg.send_emails()
                messages.info(
                    request, f"The message has been reclassified as '{ContactType(msg.subject).label}' and resent"
                )
    if reclassify_form is None:
        reclassify_form = ReclassifyForm(instance=msg)

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
            "reclassify_form": reclassify_form,
        },
    )
