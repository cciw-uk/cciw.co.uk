from django import template
from django.shortcuts import render_to_response
from django.http import Http404
from django.template import RequestContext

from cciw.cciwmain.common import *
from cciw.cciwmain.models import HtmlChunk, MenuLink

def find(request):
    try:
        link = MenuLink.objects.get(url=request.path)
    except MenuLink.DoesNotExist:
        raise Http404()

    try:
        chunk = link.htmlchunk_set.filter()[0]
    except IndexError:
        raise Http404()

    c = RequestContext(request, standard_extra_context(title=chunk.page_title))
    c['contentBody'] = chunk.render(request)
    return render_to_response('cciw/standard.html', context_instance=c)
