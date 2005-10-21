from django.core import template_loader
from django.core import template
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404

from cciw.apps.cciw.common import *
from django.models.sitecontent import *

def find(request):
	try:
		link = menulinks.get_object(url__exact=request.path)
	except menulinks.MenuLinkDoesNotExist:
		raise Http404()
	
	try:
		chunk = link.get_htmlchunk()
	except htmlchunks.HtmlChunkDoesNotExist:
		raise Http404()
	
	c = StandardContext(request, title = chunk.page_title)
	c['contentBody'] = chunk.render(c)
	t = template_loader.get_template('standard')
	# render 2: using the 'standard' template, reusing the context
	return HttpResponse(t.render(c))
