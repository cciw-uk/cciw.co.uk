from django.core import template
from django.core.extensions import render_to_response
from django.core.exceptions import Http404

from cciw.apps.cciw.common import *
from django.models.sitecontent import htmlchunks, menulinks

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
    chunk.render(c, 'contentBody')
    return render_to_response('cciw/standard', c)
