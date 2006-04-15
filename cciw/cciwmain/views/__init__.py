from django import http
from django.template import RequestContext, loader
def handler404(request, template_name='404.html'):
    t = loader.get_template(template_name)
    return http.HttpResponseNotFound(t.render(RequestContext(request)))
