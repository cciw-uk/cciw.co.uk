from django.core import template_loader
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404

from django.models.camps import sites
from django.models.sitecontent import htmlchunks
from cciw.apps.cciw.common import StandardContext

def index(request):
	t = template_loader.get_template('sites/index')
	c = StandardContext(request, title="Camp sites")
	c['sites'] =  sites.get_list()
	htmlchunks.renderIntoContext(c, {'sites_general': 'sites_general'})
	return HttpResponse(t.render(c))

def detail(request, name):
	try:
		site = sites.get_object(slugName__exact=name)
	except sites.SiteDoesNotExist:
		raise Http404
	
	c = StandardContext(request, {'site': site},
					title = site.shortName + " camp site")
	t = template_loader.get_template('sites/detail')
	return HttpResponse(t.render(c))
	
