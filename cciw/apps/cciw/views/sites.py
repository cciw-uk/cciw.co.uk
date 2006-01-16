from django.core import template_loader
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404
from django.core.extensions import DjangoContext

from django.models.camps import sites
from django.models.sitecontent import htmlchunks
from cciw.apps.cciw.common import standard_extra_context

def index(request):
    t = template_loader.get_template('cciw/sites/index')
    c = DjangoContext(request, standard_extra_context(title="Camp sites"))
    c['sites'] =  sites.get_list()
    htmlchunks.render_into_context(c, {'sites_general': 'sites_general'})
    return HttpResponse(t.render(c))

def detail(request, name):
    try:
        site = sites.get_object(slug_name__exact=name)
    except sites.SiteDoesNotExist:
        raise Http404
    
    c = DjangoContext(request, standard_extra_context({'site': site},
                    title = site.short_name + " camp site"))
    t = template_loader.get_template('cciw/sites/detail')
    return HttpResponse(t.render(c))
    
