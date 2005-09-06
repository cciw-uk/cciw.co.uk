from django.core import template_loader
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404

from django.models.camps import sites
from cciw.apps.cciw.common import StandardContext

def index(request):
	t = template_loader.get_template('sites/index')
	c = StandardContext(request, {'sites': sites.get_list() },
					title="Camp sites")
	return HttpResponse(t.render(c))

def detail(request, name):
	try:
		site = sites.get_object(slug_name__exact=name)
	except sites.SiteDoesNotExist:
		raise Http404
	
	c = StandardContext(request, {'site': site},
					title = site.short_name + " camp site")
	t = template_loader.get_template('sites/detail')
	return HttpResponse(t.render(c))
	
