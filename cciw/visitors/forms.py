from django import forms
from django.forms.models import ModelForm
from django.http import HttpRequest

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.visitors.models import VisitorLog


class VisitorLogForm(ModelForm):
    class Meta:
        model = VisitorLog
        fields = ["camp", "guest_name", "arrived_on", "left_on", "purpose_of_visit"]
        widgets = {
            "arrived_on": forms.DateInput(attrs={"type": "date"}),
            "left_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["camp"].queryset = Camp.objects.filter(year=common.get_thisyear())

    def save(self, request: HttpRequest) -> VisitorLog:
        log = super().save(commit=False)
        log.remote_addr = get_remote_addr(request)
        log.logged_by = user if (user := request.user).is_authenticated else None
        log.save()
        return log


def get_remote_addr(request: HttpRequest) -> str:
    if (x_forwarded_for := request.headers.get("X-Forwarded-For", "")) and x_forwarded_for != "127.0.0.1":
        return x_forwarded_for

    # Fallback that is used in tests:
    return request.META.get("REMOTE_ADDR", "")
