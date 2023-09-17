from collections.abc import Callable
from datetime import date

from django.conf import settings
from django.contrib.admin import site as admin_site
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import wordwrap
from django.template.response import TemplateResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from cciw.accounts.models import User
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.utils.views import for_htmx

from ..applications import (
    camps_for_application,
)
from ..dbs import get_officers_with_dbs_info_for_camps
from ..email import (
    send_dbs_consent_alert_leaders_email,
    send_request_for_dbs_form_email,
)
from ..forms import (
    DBSCheckForm,
    DbsConsentProblemForm,
    RequestDbsFormForm,
)
from ..models import (
    Application,
    DBSActionLogType,
    DBSCheck,
)
from .utils.auth import (
    dbs_officer_or_camp_admin_required,
    dbs_officer_required,
)
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs
from .utils.htmx import add_hx_trigger_header


@staff_member_required
@dbs_officer_or_camp_admin_required
@ensure_csrf_cookie
@with_breadcrumbs(officers_breadcrumbs)
@for_htmx(use_block_from_params=True)
def manage_dbss(request, year: int) -> HttpResponse:
    # We need a lot of information. Try to get it in a few up-front queries
    camps = list(Camp.objects.filter(year=year).order_by("camp_name__slug"))
    if len(camps) == 0:
        raise Http404

    # Selected camps:
    # We need to support URLs that indicate which camp to select, so we
    # can permalink nicely.
    if "camp" in request.GET:
        selected_camp_slugs = set(request.GET.getlist("camp"))
        selected_camps = {c for c in camps if c.slug_name in selected_camp_slugs}
    else:
        if "Hx-Request" in request.headers and request.GET.get("use_block", "") == "content":
            # They deselected the last checkbox, we should show them nothing for UI consistency.
            # In other cases (e.g. use_block = table-body, officer_id=...), we should include all camps.
            selected_camps = set()
        else:
            # Assume all, because having none is never useful
            selected_camps = set(camps)

    try:
        officer_id = int(request.GET["officer_id"])
    except (KeyError, ValueError):
        officer_id = None

    officers_and_dbs_info = get_officers_with_dbs_info_for_camps(camps, selected_camps, officer_id=officer_id)

    return TemplateResponse(
        request,
        "cciw/officers/manage_dbss.html",
        {
            "title": f"Manage DBSs {year}",
            "officers_and_dbs_info": officers_and_dbs_info,
            "camps": camps,
            "selected_camps": selected_camps,
            "year": year,
            "CheckType": DBSCheck.CheckType,
            "external_dbs_officer": settings.EXTERNAL_DBS_OFFICER,
        },
    )


def htmx_dbs_events_response(
    closeModal: bool = False,
    refreshOfficer: User | None = None,
) -> HttpResponse:
    events = {}
    if refreshOfficer is not None:
        events[f"refreshOfficer-{refreshOfficer.id}"] = True
    if closeModal:
        events["jsCloseModal"] = closeModal

    return add_hx_trigger_header(HttpResponse(""), events)


@staff_member_required
@dbs_officer_required
def mark_dbs_sent(request):
    officer_id = int(request.POST["officer_id"])
    officer = User.objects.get(id=officer_id)
    if "mark_sent" in request.POST:
        request.user.dbsactions_performed.create(officer=officer, action_type=DBSActionLogType.FORM_SENT)
    elif "undo_last_mark_sent" in request.POST:
        request.user.dbsactions_performed.remove_last(officer=officer, action_type=DBSActionLogType.FORM_SENT)

    return htmx_dbs_events_response(refreshOfficer=officer)


@staff_member_required
@dbs_officer_required
@for_htmx(use_block_from_params=True)
def dbs_consent_alert_leaders(request, application_id: int):
    app = get_object_or_404(Application.objects.filter(id=application_id))
    officer = app.officer
    camps = camps_for_application(app)
    context = {"officer": officer}
    messageform_info = {
        "application": app,
        "officer": officer,
        "camps": camps,
        "domain": common.get_current_domain(),
        "sender": request.user,
    }

    def send_email(message):
        send_dbs_consent_alert_leaders_email(message, officer, camps)
        request.user.dbsactions_performed.create(officer=officer, action_type=DBSActionLogType.LEADER_ALERT_SENT)

    return modal_dialog_message_form(
        request,
        context,
        template_name="cciw/officers/dbs_consent_alert_leaders.html",
        messageform_info=messageform_info,
        messageform_class=DbsConsentProblemForm,
        send_email=send_email,
        cancel_response=htmx_dbs_events_response(closeModal=True),
        success_response=htmx_dbs_events_response(closeModal=True, refreshOfficer=officer),
    )


@staff_member_required
@dbs_officer_required
def request_dbs_form_action(request, application_id: int):
    app = get_object_or_404(Application.objects.filter(id=application_id))
    external_dbs_officer = settings.EXTERNAL_DBS_OFFICER
    officer = app.officer
    context = {
        "officer": officer,
        "external_dbs_officer": external_dbs_officer,
    }
    messageform_info = {
        "external_dbs_officer": external_dbs_officer,
        "application": app,
        "officer": officer,
        "sender": request.user,
    }

    def send_email(message):
        send_request_for_dbs_form_email(message, officer, request.user)
        request.user.dbsactions_performed.create(
            officer=officer, action_type=DBSActionLogType.REQUEST_FOR_DBS_FORM_SENT
        )

    return modal_dialog_message_form(
        request,
        context,
        template_name="cciw/officers/request_dbs_form_action.html",
        messageform_info=messageform_info,
        messageform_class=RequestDbsFormForm,
        send_email=send_email,
        cancel_response=htmx_dbs_events_response(closeModal=True),
        success_response=htmx_dbs_events_response(closeModal=True, refreshOfficer=officer),
    )


@staff_member_required
@dbs_officer_required
@for_htmx(use_block_from_params=True)
def dbs_checked_online(request: HttpRequest, officer_id: int):
    officer = User.objects.get(id=officer_id)
    dbs_number = request.GET.get("dbs_number", "")
    old_dbs_check = officer.dbs_checks.filter(dbs_number=dbs_number).order_by("-completed").first()
    form_initial = {
        "dbs_number": dbs_number,
        "registered_with_dbs_update": True,
        "completed": date.today(),
        "check_type": DBSCheck.CheckType.ONLINE,
    }
    if old_dbs_check:
        form_initial.update(
            {
                "requested_by": old_dbs_check.requested_by,
                "other_organisation": old_dbs_check.other_organisation,
            }
        )
    return _dbscheck_create_form(request, officer, form_initial)


@staff_member_required
@dbs_officer_required
@for_htmx(use_block_from_params=True)
def dbs_register_received(request: HttpRequest, officer_id: int):
    officer = User.objects.get(id=officer_id)
    form_initial = {
        "check_type": DBSCheck.CheckType.FORM,
    }
    return _dbscheck_create_form(request, officer, form_initial)


def _dbscheck_create_form(request: HttpRequest, officer: User, form_initial: dict):
    dbscheck_admin_instance = admin_site._registry[DBSCheck]
    if request.method == "POST":
        if "save" in request.POST:
            form = DBSCheckForm(request.POST)
            if form.is_valid():
                dbs_check = form.save(officer=officer)
                # Copy what admin does for addition action
                dbscheck_admin_instance.log_addition(request, dbs_check, [{"added": {}}])
                # TODO add admin.LogEntry
                return htmx_dbs_events_response(refreshOfficer=officer, closeModal=True)
        else:
            return htmx_dbs_events_response(closeModal=True)
    else:
        if "completed" in form_initial and not isinstance(form_initial["completed"], str):
            form_initial["completed"] = form_initial["completed"].strftime("%Y-%m-%d")
        form = DBSCheckForm(initial=form_initial)

    return TemplateResponse(
        request,
        "cciw/officers/add_dbs_check.html",
        {
            "officer": officer,
            "form": form,
        },
    )


def modal_dialog_message_form(
    request,
    context,
    *,
    template_name: str,
    messageform_info: dict,
    send_email: Callable[[str], None],
    messageform_class=type,
    success_response: HttpResponse,
    cancel_response: HttpResponse,
):
    if request.method == "POST":
        if "send" in request.POST:
            messageform = messageform_class(request.POST, message_info=messageform_info)
            if messageform.is_valid():
                send_email(wordwrap(messageform.cleaned_data["message"], 70))
                return success_response
        else:
            return cancel_response
    else:
        messageform = messageform_class(message_info=messageform_info)

    context["messageform"] = messageform
    return TemplateResponse(request, template_name, context)
