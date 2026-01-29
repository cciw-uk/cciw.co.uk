from django.http import Http404, HttpRequest
from django.template.response import TemplateResponse

from cciw.sitecontent.models import MenuLink


def find(request: HttpRequest, path: str, template_name: str = "cciw/chunk_page.html") -> TemplateResponse:
    if path in ("", "/"):
        url = "/"
    else:
        url = "/" + path + "/"

    try:
        link = MenuLink.objects.get(url=url)
    except MenuLink.DoesNotExist:
        raise Http404()

    try:
        chunk = link.htmlchunk_set.filter()[0]
    except IndexError:
        raise Http404()

    return TemplateResponse(
        request,
        template_name,
        {
            "title": chunk.page_title,
            "chunk_html": chunk.render(request),
        },
    )


def home(request: HttpRequest) -> TemplateResponse:
    return find(request, "", template_name="cciw/home.html")
