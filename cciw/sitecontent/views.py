from django.conf import settings
from django.http import Http404
from django.template.response import TemplateResponse

from cciw.sitecontent.models import MenuLink
from cciw.utils.literate_yaml import literate_yaml_to_rst
from cciw.utils.rst import remove_rst_title, rst_to_html


def find(request, path: str, template_name="cciw/chunk_page.html"):
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


def home(request):
    return find(request, "", template_name="cciw/home.html")


def data_retention_policy(request):
    policy = open(settings.DATA_RETENTION_CONFIG_FILE).read()
    return TemplateResponse(
        request,
        "cciw/data_retention_policy.html",
        {
            "title": "Data retention policy",
            "data_retention_policy": rst_to_html(
                remove_rst_title(literate_yaml_to_rst(policy)), initial_header_level=2
            ),
        },
    )
