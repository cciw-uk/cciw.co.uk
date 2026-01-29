from django.db import models
from django.http import HttpRequest
from django.http.response import HttpResponse, HttpResponseRedirect

from .views import reroute_response


class RerouteResponseAdminMixin:
    """
    Admin mixin that allows a different return URL to
    be substituted using a '_return_to' query string parameter.
    """

    def conditional_reroute(self, request: HttpRequest, main_response: HttpResponseRedirect) -> HttpResponse:
        response = reroute_response(request, default_to_close=False)
        if response is not None:
            return response
        return main_response

    def response_post_save_add(self, request: HttpRequest, obj: models.Model) -> HttpResponse:
        return self.conditional_reroute(request, super().response_post_save_add(request, obj))

    def response_post_save_change(self, request: HttpRequest, obj: models.Model) -> HttpResponse:
        return self.conditional_reroute(request, super().response_post_save_change(request, obj))
