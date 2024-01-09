from django import forms
from django.conf import settings
from django.core import mail
from django.template import loader
from django.template.response import TemplateResponse
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.ipn.models import PayPalIPN

from cciw.cciwmain import common
from cciw.cciwmain.common import get_current_domain
from cciw.cciwmain.forms import CciwFormMixin


class DonateForm(CciwFormMixin, forms.Form):
    # Field lengths match PayPal
    first_name = forms.CharField(max_length=32, required=False)
    last_name = forms.CharField(max_length=32, required=False)
    email = forms.EmailField(
        max_length=127,
        required=False,
    )
    amount = forms.IntegerField(widget=forms.widgets.NumberInput, help_text="The amount you wish to donate")


DONATION_CUSTOM_VALUE = "donation"


def donate(request):
    domain = get_current_domain()
    protocol = "https" if request.is_secure() else "http"

    paypal_form = None
    if request.method == "POST":
        form = DonateForm(request.POST)
        if form.is_valid():
            paypal_dict = {
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data["last_name"],
                "payer_email": form.cleaned_data["email"],  # not sure if it is payer_email or email
                "email": form.cleaned_data["email"],
                "amount": str(form.cleaned_data["amount"]),
                "business": settings.PAYPAL_RECEIVER_EMAIL,
                "item_name": "Donation",
                "notify_url": f"{protocol}://{domain}{reverse('paypal-ipn')}",
                "return": f"{protocol}://{domain}{reverse('cciw-donations-donate_done')}",
                "cancel_return": f"{protocol}://{domain}{reverse('cciw-donations-donate')}",
                "custom": DONATION_CUSTOM_VALUE,
                "currency_code": "GBP",
                "no_note": "1",
                "no_shipping": "1",
            }
            paypal_form = PayPalPaymentsForm(initial=paypal_dict, button_type="donate")
    else:
        form = DonateForm()

    return TemplateResponse(
        request,
        "cciw/donations/donate.html",
        {
            "title": "Donate to CCiW",
            "donate_form": form,
            "paypal_form": paypal_form,
        },
    )


def donate_done(request):
    return TemplateResponse(
        request,
        "cciw/donations/donate_done.html",
        {
            "title": "Thank you!",
        },
    )


def send_donation_received_email(ipn: PayPalIPN) -> None:
    body = loader.render_to_string(
        "cciw/donations/donation_received_email.txt",
        {
            "domain": common.get_current_domain(),
            "ipn_obj": ipn,
        },
    )
    subject = "[CCIW] Donation received"
    mail.send_mail(subject, body, settings.WEBMASTER_FROM_EMAIL, settings.EMAIL_RECIPIENTS["FINANCE"])
