from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from furl.furl import furl

from cciw.visitors.forms import VisitorLogForm
from cciw.visitors.models import VisitorLog


def create_visitor_log(request) -> HttpResponse:
    if request.method == "POST":
        form = VisitorLogForm(data=request.POST)
        if form.is_valid():
            log: VisitorLog = form.save(request=request)
            messages.info(
                request,
                f'Thank you for submitting the information regarding visitor "{log.guest_name}", it has been saved to the visitors book. '
                + "You can add another entry below if you need to, which has been pre-filled with some previous values.",
            )

            url = furl(reverse("cciw-visitors-create_log"))
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
