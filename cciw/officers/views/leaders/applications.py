"""
Views relating to leaders managing application forms
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from cciw.cciwmain.common import CampId
from cciw.mail.lists import address_for_camp_slackers

from ...applications import (
    applications_for_camp,
)
from ...utils import camp_serious_slacker_list, camp_slacker_list
from ..utils.auth import (
    camp_admin_required,
)
from ..utils.breadcrumbs import leaders_breadcrumbs, with_breadcrumbs
from ..utils.campid import get_camp_or_404


@staff_member_required
@camp_admin_required
@never_cache
@with_breadcrumbs(leaders_breadcrumbs)
def manage_applications(request: HttpRequest, camp_id: CampId) -> TemplateResponse:
    camp = get_camp_or_404(camp_id)
    finished_applications = (
        applications_for_camp(camp).order_by("officer__first_name", "officer__last_name").with_references()
    )
    return TemplateResponse(
        request,
        "cciw/officers/manage_applications.html",
        {
            "title": f"Manage applications: {camp.nice_name}",
            "camp": camp,
            "finished_applications": finished_applications,
        },
    )


@staff_member_required
@camp_admin_required
@with_breadcrumbs(leaders_breadcrumbs)
def officer_application_status(request: HttpRequest, camp_id: CampId) -> TemplateResponse:
    camp = get_camp_or_404(camp_id)
    return TemplateResponse(
        request,
        "cciw/officers/officer_application_status.html",
        {
            "camp": camp,
            "title": f"Application form status: {camp.nice_name}",
            "officers_noapplicationform": camp_slacker_list(camp),
            "address_noapplicationform": address_for_camp_slackers(camp),
            "officers_serious_slackers": camp_serious_slacker_list(camp),
        },
    )
