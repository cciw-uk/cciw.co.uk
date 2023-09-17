from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse

from cciw.cciwmain.utils import get_protected_download

from .utils.auth import potential_camp_officer_required
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs


@staff_member_required
@potential_camp_officer_required
def officer_files(request, path: str):
    return get_protected_download("officers", path)


@staff_member_required
@with_breadcrumbs(officers_breadcrumbs)
def officer_info(request):
    return TemplateResponse(
        request,
        "cciw/officers/info.html",
        {
            "title": "Information for officers",
            "show_wiki_link": request.user.is_wiki_user,
        },
    )
