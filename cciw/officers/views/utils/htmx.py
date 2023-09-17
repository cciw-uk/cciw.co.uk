import json

from django.http import HttpResponse


def add_hx_trigger_header(response: HttpResponse, events: dict) -> HttpResponse:
    if events:
        response.headers["Hx-Trigger"] = json.dumps(events)
    return response
