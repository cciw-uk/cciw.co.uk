from django.http import Http404
from django.shortcuts import render

from cciw.sitecontent.models import MenuLink


def find(request, path, template_name='cciw/chunk_page.html'):
    if path in ('', '/'):
        url = '/'
    else:
        url = '/' + path + '/'

    try:
        link = MenuLink.objects.get(url=url)
    except MenuLink.DoesNotExist:
        raise Http404()

    try:
        chunk = link.htmlchunk_set.filter()[0]
    except IndexError:
        raise Http404()

    c = dict(title=chunk.page_title)
    c['chunk_html'] = chunk.render(request)
    return render(request, template_name, c)


def home(request):
    return find(request, '', template_name='cciw/home.html')
