from django import http
from django.http import HttpRequest
from django.http.response import Http404, HttpResponseNotFound
from django.template import loader


def handler404(request: HttpRequest, exception: Http404, template_name: str = "404.html") -> HttpResponseNotFound:
    t = loader.get_template(template_name)
    return http.HttpResponseNotFound(t.render({}, request=request))


# For debugging
def show404(request):
    return handler404(request, None)


def show500(request):
    t = loader.get_template("500.html")
    return http.HttpResponse(t.render({}, request=None))
