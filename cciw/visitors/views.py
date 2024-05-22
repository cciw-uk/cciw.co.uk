from datetime import date

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.crypto import salted_hmac
from furl.furl import furl

from cciw.cciwmain import common
from cciw.visitors.forms import VisitorLogForm
from cciw.visitors.models import VisitorLog


def make_visitor_log_token(year: int) -> str:
    # Relatively low security needed on this, and people might need to be
    # entering the link manually, so we use just 8 digits.
    return salted_hmac("cciw.visitors.create_visitor_log", f"year:{year}").hexdigest()[0:8]


def make_visitor_log_url(year: int) -> str:
    return reverse("cciw-visitors-create_log", kwargs={"token": make_visitor_log_token(year)})


def create_visitor_log(request: HttpRequest, token: str) -> HttpResponse:
    correct_token = make_visitor_log_token(common.get_thisyear())

    if token.lower() != correct_token:
        return TemplateResponse(request, "cciw/visitors/create_log.html", {"incorrect_url": True})

    if request.method == "POST":
        form = VisitorLogForm(data=request.POST)
        if form.is_valid():
            log: VisitorLog = form.save(request=request)
            messages.info(
                request,
                f'Thank you for submitting the information regarding visitor "{log.guest_name}", it has been saved to the visitors book. '
                + "You can add another entry below if you need to, which has been pre-filled with some previous values.",
            )

            url = furl(reverse("cciw-visitors-create_log", kwargs={"token": token}))
            url = url.add(
                {
                    "camp": log.camp.id,
                    "purpose_of_visit": log.purpose_of_visit,
                    "arrived_on": log.arrived_on.strftime("%Y-%m-%d"),
                    "left_on": log.left_on.strftime("%Y-%m-%d"),
                }
            )
            return redirect(str(url))

    else:
        initial = {
            # HACK the strftime should be done by the widget/field
            "arrived_on": date.today().strftime("%Y-%m-%d"),
            "left_on": date.today().strftime("%Y-%m-%d"),
        }
        for attr in ["camp", "purpose_of_visit", "arrived_on", "left_on"]:
            if (val := request.GET.get(attr, None)) is not None:
                initial[attr] = val
        form = VisitorLogForm(initial=initial)
    return TemplateResponse(request, "cciw/visitors/create_log.html", {"form": form})
