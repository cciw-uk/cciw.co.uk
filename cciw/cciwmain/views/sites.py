from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from cciw.cciwmain.models import Site


def index(request):
    return TemplateResponse(
        request,
        "cciw/sites/index.html",
        {
            "title": "Camp sites",
            "sites": Site.objects.all(),
        },
    )


def detail(request, slug: str):
    return TemplateResponse(
        request,
        "cciw/sites/detail.html",
        {
            "site": get_object_or_404(Site.objects.filter(slug_name=slug)),
        },
    )
