import furl
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls.resolvers import ResolverMatch, get_resolver
from django.views.decorators.http import require_POST

from cciw.accounts.models import User
from cciw.cciwmain.common import CampId
from cciw.mail.lists import address_for_camp_officers
from cciw.utils.views import for_htmx, get_redirect_from_request, make_get_request

from ...create import email_officer
from ...forms import (
    CreateOfficerForm,
    UpdateOfficerForm,
)
from ...models import (
    CampRole,
    Invitation,
    OfficerList,
    add_officer_to_camp,
    remove_officer_from_camp,
)
from ...utils import officer_data_to_spreadsheet
from ..utils.auth import (
    camp_admin_required,
)
from ..utils.breadcrumbs import leaders_breadcrumbs, with_breadcrumbs
from ..utils.campid import get_camp_or_404
from ..utils.data_retention import DataRetentionNotice, show_data_retention_notice
from ..utils.spreadsheets import spreadsheet_response


@staff_member_required
@camp_admin_required
@for_htmx(use_block_from_params=True)
@with_breadcrumbs(leaders_breadcrumbs)
def officer_list(
    request: HttpRequest,
    camp_id: CampId,
) -> HttpResponse:
    return _officer_list(request, camp_id)


# undecorated for internal redirect use
def _officer_list(
    request: HttpRequest,
    camp_id: CampId,
    *,
    selected_officers: set[User] | None = None,
    open_chooseofficers: bool | None = None,
    search_query: str = "",
    selected_role: int | None = None,
    add_officer_message: str = "",
) -> TemplateResponse:
    camp = get_camp_or_404(camp_id)
    officer_list = OfficerList(camp)
    camp_roles = CampRole.objects.all()

    readonly = camp.is_past()
    try:
        # From create_officer view
        created_officer = User.objects.get(id=int(request.GET.get("created_officer_id", "")))
    except (ValueError, User.DoesNotExist):
        created_officer = None

    selected_officers = selected_officers or set()

    if request.method == "POST" and not readonly:
        # "Add officer" functionality
        chosen_officers = [
            officer for officer in officer_list.addable_officers if f"chooseofficer_{officer.id}" in request.POST
        ]
        add_previous_role = "add_previous_role" in request.POST
        add_new_role = "add_new_role" in request.POST
        if add_previous_role or add_new_role:
            if add_new_role:
                new_role = CampRole.objects.get(id=int(request.POST["new_role"]))
                added_officers = [add_officer_to_camp(camp, o, new_role) for o in chosen_officers]
            elif add_previous_role:
                added_officers = [
                    add_officer_to_camp(camp, o, role)
                    for o in chosen_officers
                    if (role := officer_list.get_previous_role(o)) is not None
                ]
            else:
                added_officers = []
            # if we successfully process, we remove from chosen_officer_ids,
            # but preserve the state of checkboxes we weren't able to handle.
            selected_officers = set(chosen_officers) - set(added_officers)
            if selected_officers:
                add_officer_message = "Some officers could not be added because their previous role is not known"

        # "Remove officer" functionality
        if "remove" in request.POST:
            remove_officer_from_camp(camp, User.objects.get(id=int(request.POST["officer_id"])))

        # Internal redirect, to refresh data from DB
        return _officer_list(
            make_get_request(request),
            camp_id=camp.url_id,
            # Propagate some state from POST:
            selected_officers=selected_officers,
            open_chooseofficers=bool(chosen_officers),  # if we just added some, probably want to add more
            search_query=request.POST.get("search", ""),
            selected_role=int(request.POST["new_role"]) if ("new_role" in request.POST) else None,
            add_officer_message=add_officer_message,
        )

    # Should the 'choose officers' component default to open?
    if open_chooseofficers is None:
        open_chooseofficers = (
            len(officer_list.invitations) == 0  # no officers added yet
            or created_officer is not None  # just created one in system, will want to add them
        )
    context = {
        "camp": camp,
        "title": f"Officer list: {camp.nice_name}, {camp.leaders_formatted}",
        "invitations": officer_list.invitations,
        "candidate_officers": officer_list.candidate_officers,
        "open_chooseofficers": open_chooseofficers,
        "selected_officers": selected_officers,
        "add_officer_message": add_officer_message,
        "camp_roles": camp_roles,
        "selected_role": selected_role,
        "address_all": address_for_camp_officers(camp),
        "created_officer": created_officer,
        "search_query": search_query,
        "readonly": readonly,
    }

    return TemplateResponse(request, "cciw/officers/officer_list.html", context)


@staff_member_required
@camp_admin_required
def update_officer(request: HttpRequest) -> HttpResponse:
    # Partial page, via htmx
    invitation = Invitation.objects.select_related("role", "officer").get(id=int(request.GET["invitation_id"]))
    officer = invitation.officer
    mode = "edit"
    if request.method == "POST":
        if "save" in request.POST:
            form = UpdateOfficerForm(data=request.POST, instance=officer, invitation=invitation)
            if form.is_valid():
                form.save()
                mode = "display"
        else:
            # Cancel
            mode = "display"
            form = None
    else:
        form = UpdateOfficerForm(instance=officer, invitation=invitation)

    return TemplateResponse(
        request,
        "cciw/officers/officer_list_officer_row_inc.html",
        {
            "mode": mode,
            "form": form,
            "invitation": invitation,
        },
    )


@staff_member_required
@camp_admin_required
@with_breadcrumbs(leaders_breadcrumbs)
def create_officer(request: HttpRequest) -> HttpResponse:
    duplicate_message, allow_confirm, existing_users = "", True, []
    message = ""
    if request.method == "POST":
        form = CreateOfficerForm(request.POST)
        process_form = False
        if form.is_valid():
            duplicate_message, allow_confirm, existing_users = form.check_duplicates()
            if "add" in request.POST:
                # If no duplicates, we can process without confirmation
                if not duplicate_message:
                    process_form = True

            elif allow_confirm and "confirm" in request.POST:
                process_form = True

            if process_form:
                u = form.save()
                redirect_resp = get_redirect_from_request(request)
                if redirect_resp:
                    redirect_url = redirect_resp["Location"]
                    message = f"Officer {u.full_name} has been added to the system and emailed."
                    match: ResolverMatch = get_resolver().resolve(redirect_url)
                    if match is not None and match.func == officer_list:
                        message += " Don't forget to choose a role and add them to your officer list!"

                    redirect_resp["Location"] = furl.furl(redirect_url).add({"created_officer_id": u.id}).url
                    messages.info(request, message)
                    return redirect_resp
                else:
                    messages.info(
                        request,
                        f"Officer {u.full_name} has been added and emailed.  You can add another if required.",
                    )
                return HttpResponseRedirect(".")

    else:
        form = CreateOfficerForm()

    return TemplateResponse(
        request,
        "cciw/officers/create_officer.html",
        {
            "title": "Add officer to system",
            "form": form,
            "duplicate_message": duplicate_message,
            "existing_users": existing_users,
            "allow_confirm": allow_confirm,
            "message": message,
        },
    )


@staff_member_required
@camp_admin_required
@require_POST
def resend_email(request: HttpRequest) -> HttpResponse:
    officer_id = int(request.POST["officer_id"])
    user = User.objects.get(pk=officer_id)
    email_officer(user, update=True)
    return TemplateResponse(
        request,
        "cciw/officers/resend_email_form_inc.html",
        {
            "officer_id": officer_id,
            "caption": "Sent!",
        },
    )


@staff_member_required
@camp_admin_required
@show_data_retention_notice(DataRetentionNotice.OFFICERS, "Officer data")
def export_officer_data(request: HttpRequest, camp_id: CampId) -> HttpResponse:
    camp = get_camp_or_404(camp_id)
    return spreadsheet_response(
        officer_data_to_spreadsheet(camp),
        f"CCIW-camp-{camp.url_id}-officers",
        notice=DataRetentionNotice.OFFICERS,
    )
