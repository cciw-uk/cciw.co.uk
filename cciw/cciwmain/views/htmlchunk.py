from django.shortcuts import render
from django.http import Http404

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

    c = dict(title=chunk.page_title)
    c['contentBody'] = chunk.render(request)
    return render(request, 'cciw/standard.html', c)
