from django import http
from django.template import loader


def handler404(request, exception, template_name='404.html'):
    t = loader.get_template(template_name)
    return http.HttpResponseNotFound(t.render({}, request=request))


# For debugging
def show404(request):
    return handler404(request, None)


def show500(request):
    t = loader.get_template("500.html")
    return http.HttpResponse(t.render({}, request=None))
