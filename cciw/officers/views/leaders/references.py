from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import wordwrap
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import cache_control, never_cache

from cciw.accounts.models import User
from cciw.cciwmain.common import CampId
from cciw.utils.views import for_htmx

from ...applications import (
    applications_for_camp,
)
from ...email import (
    make_ref_form_url,
    send_nag_by_officer,
    send_reference_request_email,
)
from ...forms import (
    AdminReferenceForm,
    CorrectRefereeDetailsForm,
    SendNagByOfficerForm,
    SendReferenceRequestForm,
)
from ...models import (
    Referee,
    Reference,
    ReferenceAction,
    add_previous_references,
    get_previous_references,
)
from ..referees import get_initial_reference_form
from ..utils.auth import (
    camp_admin_required,
)
from ..utils.breadcrumbs import leaders_breadcrumbs, with_breadcrumbs
from ..utils.campid import get_camp_or_404
from ..utils.htmx import add_hx_trigger_header


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
@never_cache
@with_breadcrumbs(leaders_breadcrumbs)
@for_htmx(use_block_from_params=True)
def manage_references(request, camp_id: CampId):
    # If referee_id is set, we just want to update part of the page.
    referee_id = request.GET.get("referee_id")
    officer = None
    officer_id = request.GET.get("officer_id")
    if officer_id is not None:
        try:
            officer = User.objects.get(id=int(officer_id))
        except (ValueError, User.DoesNotExist):
            raise Http404
    camp = get_camp_or_404(camp_id)

    if referee_id is None:
        apps = applications_for_camp(camp, officer_ids=[officer_id] if officer is not None else None)
        app_ids = [app.id for app in apps]
        referees = Referee.objects.filter(application__in=app_ids).order_by()
    else:
        referees = Referee.objects.filter(pk=referee_id).order_by()

    referees = referees.prefetch_related(
        Prefetch("actions", queryset=ReferenceAction.objects.select_related("user"))
    ).select_related("reference", "application", "application__officer")

    all_referees = list(referees)
    if "ref_email" in request.GET:
        ref_email = request.GET["ref_email"]
        all_referees = [r for r in all_referees if r.email.lower() == ref_email.lower()]
    else:
        ref_email = None

    for referee in all_referees:
        referee.sort_key = [
            # Received come last:
            referee.reference_is_received(),
            # Not requested come first:
            referee.reference_was_requested(),
            # Then sort by:
            referee.application.officer.first_name,
            referee.application.officer.last_name,
            referee.name,
        ]
        # Note that we add this as an attribute because we also need to sort by
        # the same key client side.
        if referee.reference_is_received():
            continue  # Don't need the following
        # decorate each Reference with suggested previous References.
        add_previous_references(referee)

    all_referees.sort(key=lambda referee: referee.sort_key)

    return TemplateResponse(
        request,
        "cciw/officers/manage_references.html",
        {
            "officer": officer,
            "camp": camp,
            "title": f"Manage references: {camp.nice_name}",
            "ref_email_search": ref_email,
            "all_referees": all_referees,
        },
    )


@staff_member_required
@camp_admin_required
@for_htmx(use_block_from_params=True)
def correct_referee_details(request: HttpRequest, camp_id: CampId, referee_id: int):
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    if request.method == "POST":
        if "save" in request.POST:
            form = CorrectRefereeDetailsForm(request.POST, instance=referee)
            if form.is_valid():
                form.save()
                referee.log_details_corrected(request.user, timezone.now())
                return htmx_reference_events_response(closeModal=True, refreshReferee=referee)
        else:
            # cancel
            return htmx_reference_events_response(closeModal=True)
    else:
        form = CorrectRefereeDetailsForm(instance=referee)

    return TemplateResponse(
        request,
        "cciw/officers/correct_referee_details.html",
        {
            "form": form,
            "referee": referee,
        },
    )


def _get_previous_reference(referee: Referee, prev_ref_id: int) -> tuple[bool, Reference | None]:
    """
    Get previous reference that matches prev_ref_id, returning:
    (
       bool indicating an exact previous reference match,
       previous reference

    """
    exact_prev_reference, prev_references = get_previous_references(referee)

    if exact_prev_reference is not None:
        if exact_prev_reference.id != prev_ref_id:
            # This could happen only if the user has fiddled with URLs, or
            # there has been some update on the page.
            return (False, None)
        return (True, exact_prev_reference)
    else:
        # Get old referee data
        prev_references = [r for r in prev_references if r.id == prev_ref_id]
        if len(prev_references) != 1:
            return (False, None)
        return (False, prev_references[0])


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
@for_htmx(use_block_from_params=True)
def request_reference(request: HttpRequest, camp_id: CampId, referee_id: int):
    camp = get_camp_or_404(camp_id)
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    app = referee.application

    context = {}
    # Work out 'old_referee' or 'known_email_address', and the URL to use in the
    # message.
    try:
        prev_ref_id = int(request.GET["prev_ref_id"])
    except (KeyError, ValueError):
        prev_ref_id = None
    if prev_ref_id:
        prev_reference_is_exact, prev_reference = _get_previous_reference(referee, prev_ref_id)
        if prev_reference is None:
            return htmx_reference_events_response(closeModal=True, refreshReferee=referee)
        context["known_email_address"] = prev_reference_is_exact
        context["old_referee"] = prev_reference.referee
        url = make_ref_form_url(referee.id, prev_ref_id)
    else:
        url = make_ref_form_url(referee.id, None)
        prev_reference = None

    messageform_info = dict(
        referee=referee,
        applicant=app.officer,
        camp=camp,
        url=url,
        sender=request.user,
        update=prev_reference is not None,
    )

    if request.method == "POST":
        if "send" in request.POST:
            context["show_messageform"] = True
            form = SendReferenceRequestForm(request.POST, message_info=messageform_info)
            if form.is_valid():
                send_reference_request_email(wordwrap(form.cleaned_data["message"], 70), referee, request.user, camp)
                referee.log_request_made(request.user, timezone.now())
                return htmx_reference_events_response(closeModal=True, refreshReferee=referee)
        elif "cancel" in request.POST:
            return htmx_reference_events_response(closeModal=True)
    else:
        form = SendReferenceRequestForm(message_info=messageform_info)

    context.update(
        {
            "already_requested": referee.reference_was_requested(),
            "referee": referee,
            "app": app,
            "is_update": prev_reference is not None,
            "form": form,
        }
    )

    return TemplateResponse(request, "cciw/officers/request_reference.html", context)


@staff_member_required
@camp_admin_required
@for_htmx(use_block_from_params=True)
def fill_in_reference_manually(request: HttpRequest, camp_id: CampId, referee_id: int):
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    reference = referee.reference if hasattr(referee, "reference") else None

    try:
        prev_ref_id = int(request.GET["prev_ref_id"])
    except (KeyError, ValueError):
        prev_ref_id = None
    if prev_ref_id:
        _, prev_reference = _get_previous_reference(referee, prev_ref_id)
    else:
        prev_reference = None

    if request.method == "POST":
        if "save" in request.POST:
            form = AdminReferenceForm(request.POST, instance=reference)
            if form.is_valid():
                form.save(referee, previous_reference=prev_reference, user=request.user)
                return htmx_reference_events_response(closeModal=True, refreshReferee=referee)
        else:
            # Cancel
            return htmx_reference_events_response(closeModal=True)
    else:
        form = get_initial_reference_form(reference, referee, prev_reference, AdminReferenceForm)

    return TemplateResponse(
        request,
        "cciw/officers/fill_in_reference_manually.html",
        {
            "referee": referee,
            "app": referee.application,
            "form": form,
            "is_update": prev_reference is not None,
        },
    )


@staff_member_required
@camp_admin_required
@for_htmx(use_block_from_params=True)
def nag_by_officer(request: HttpRequest, camp_id: CampId, referee_id: int):
    # htmx only view, runs in modal dialog
    camp = get_camp_or_404(camp_id)
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    app = referee.application
    officer = app.officer

    messageform_info = dict(referee=referee, officer=officer, sender=request.user, camp=camp)

    if request.method == "POST":
        if "send" in request.POST:
            form = SendNagByOfficerForm(request.POST, message_info=messageform_info)
            if form.is_valid():
                send_nag_by_officer(wordwrap(form.cleaned_data["message"], 70), officer, referee, request.user)
                referee.log_nag_made(request.user, timezone.now())
                return htmx_reference_events_response(closeModal=True, refreshReferee=referee)
        else:
            # cancel
            return htmx_reference_events_response(closeModal=True)
    else:
        form = SendNagByOfficerForm(message_info=messageform_info)

    return TemplateResponse(
        request,
        "cciw/officers/nag_by_officer.html",
        {
            "referee": referee,
            "app": app,
            "officer": officer,
            "form": form,
        },
    )


@staff_member_required
@camp_admin_required
@cache_control(max_age=3600)
def view_reference(request, reference_id: int):
    reference = get_object_or_404(Reference.objects.filter(id=reference_id))
    return TemplateResponse(
        request,
        "cciw/officers/view_reference_form.html",
        {
            "reference": reference,
            "officer": reference.referee.application.officer,
            "referee": reference.referee,
            "is_popup": True,
        },
    )


def htmx_reference_events_response(
    *,
    closeModal: bool = False,
    refreshReferee: Referee | None = None,
):
    events = {}
    if refreshReferee is not None:
        events[f"refreshReferee-{refreshReferee.id}"] = True
    if closeModal:
        events["jsCloseModal"] = closeModal

    return add_hx_trigger_header(HttpResponse(""), events)


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
@cache_control(max_age=3600)
def officer_history(request, officer_id: int):
    officer = get_object_or_404(User.objects.filter(id=officer_id))
    referee_pairs = [app.referees for app in (officer.applications.all().with_references().order_by("-saved_on"))]

    return TemplateResponse(
        request,
        "cciw/officers/officer_history.html",
        {
            "officer": officer,
            "referee_pairs": referee_pairs,
        },
    )
