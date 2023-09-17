"""
Views relating to officers submitting and viewing their application forms.
"""


from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache

from cciw.accounts.models import User
from cciw.cciwmain import common
from cciw.officers.applications import (
    application_rtf_filename,
    application_to_rtf,
    application_to_text,
    application_txt_filename,
    thisyears_applications,
)

from ..email_utils import formatted_email, send_mail_with_attachments
from ..models import (
    Application,
)
from .utils.breadcrumbs import officers_breadcrumbs, with_breadcrumbs


@staff_member_required
@never_cache
@with_breadcrumbs(officers_breadcrumbs)
def applications(request):
    """Displays a list of tasks related to applications."""
    user = request.user
    finished_applications = user.applications.filter(finished=True).order_by("-date_saved")
    # A NULL date_saved means they never pressed save, so there is no point
    # re-editing, so we ignore them.
    unfinished_applications = (
        user.applications.filter(finished=False).exclude(date_saved__isnull=True).order_by("-date_saved")
    )
    has_thisyears_app = thisyears_applications(user).exists()
    has_completed_app = thisyears_applications(user).filter(finished=True).exists()

    context = {
        "camps": [i.camp for i in user.invitations.filter(camp__year=common.get_thisyear())],
        "title": "Your applications",
        "finished_applications": finished_applications,
        "unfinished_applications": unfinished_applications,
        "has_thisyears_app": has_thisyears_app,
        "has_completed_app": has_completed_app,
    }

    if not has_completed_app and unfinished_applications and "edit" in request.POST:
        # Edit existing application.
        # It should now only be possible for there to be one unfinished
        # application, so we just continue with the most recent.
        return HttpResponseRedirect(reverse("admin:officers_application_change", args=(unfinished_applications[0].id,)))
    elif not has_thisyears_app and "new" in request.POST:
        # Create new application based on old one
        if finished_applications:
            new_obj = _copy_application(finished_applications[0])
        else:
            new_obj = Application.objects.create(officer=user, full_name=user.full_name)

        return HttpResponseRedirect(f"/admin/officers/application/{new_obj.id}/")

    return TemplateResponse(request, "cciw/officers/applications.html", context)


def _copy_application(application):
    new_obj = Application(id=None)
    for field in Application._meta.fields:
        if field.attname != "id":
            setattr(new_obj, field.attname, getattr(application, field.attname))
    new_obj.youth_work_declined = None
    new_obj.relevant_illness = None
    new_obj.crime_declaration = None
    new_obj.court_declaration = None
    new_obj.concern_declaration = None
    new_obj.allegation_declaration = None
    new_obj.dbs_check_consent = None
    new_obj.finished = False
    new_obj.date_saved = None
    new_obj.save()

    for old_ref, new_ref in zip(application.referees, new_obj.referees):
        for f in ["name", "address", "tel", "mobile", "email"]:
            setattr(new_ref, f, getattr(old_ref, f))
        new_ref.save()

    for q in application.qualifications.all():
        new_q = q.copy(application=new_obj)
        new_q.save()

    return new_obj


@staff_member_required
def get_application(request):
    try:
        application_id = int(request.POST["application"])
    except (KeyError, ValueError):
        raise Http404

    app = get_object_or_404(request.user.applications, id=application_id)

    format = request.POST.get("format", "")
    if format == "html":
        return HttpResponseRedirect(
            reverse("cciw-officers-view_application", kwargs=dict(application_id=application_id))
        )
    elif format == "txt":
        resp = HttpResponse(application_to_text(app), content_type="text/plain")
        resp["Content-Disposition"] = f"attachment; filename={application_txt_filename(app)}"
        return resp
    elif format == "rtf":
        resp = HttpResponse(application_to_rtf(app), content_type="text/rtf")
        resp["Content-Disposition"] = f"attachment; filename={application_rtf_filename(app)}"
        return resp
    elif format == "send":
        application_text = application_to_text(app)
        application_rtf = application_to_rtf(app)
        rtf_attachment = (application_rtf_filename(app), application_rtf, "text/rtf")

        msg = f"""Dear {request.user.first_name},

Please find attached a copy of the application you requested
 -- in plain text below and an RTF version attached.

"""
        msg = msg + application_text

        send_mail_with_attachments(
            f"[CCIW] Copy of CCiW application - {app.full_name}",
            msg,
            settings.SERVER_EMAIL,
            [formatted_email(request.user)],
            attachments=[rtf_attachment],
        )
        messages.info(request, "Email sent.")

        # Redirect back where we came from
        return HttpResponseRedirect(request.POST.get("to", "/officers/"))

    else:
        raise Http404

    return resp


@staff_member_required
def view_application_redirect(request):
    if "application_id" in request.GET:
        return HttpResponseRedirect(
            reverse("cciw-officers-view_application", kwargs=dict(application_id=request.GET["application_id"]))
        )
    raise Http404


@staff_member_required
@cache_control(max_age=3600)
@with_breadcrumbs(officers_breadcrumbs)
def view_application(request, application_id: int):
    application = get_object_or_404(Application, id=application_id)

    if application.officer_id != request.user.id and not request.user.can_manage_application_forms:
        raise PermissionDenied

    # NB, this is is called by both normal users and leaders.
    # In the latter case, request.user != app.officer

    return TemplateResponse(
        request,
        "cciw/officers/view_application.html",
        {
            "application": application,
            "officer": application.officer,
            "is_popup": True,
        },
    )


def correct_email(request):
    context = {}
    try:
        username, new_email = signing.loads(
            request.GET.get("t", ""), salt="cciw-officers-correct_email", max_age=60 * 60 * 24 * 10
        )  # 10 days
    except signing.BadSignature:
        context["message"] = (
            "The URL was invalid. Please ensure you copied the URL from the email correctly, "
            "or contact the webmaster if you are having difficulties"
        )
    else:
        u = get_object_or_404(User.objects.filter(username=username))
        u.email = new_email
        u.save()
        context["message"] = "Your email address has been updated, thanks."
        context["success"] = True

    return TemplateResponse(request, "cciw/officers/email_update.html", context)


def correct_application(request):
    context = {}
    try:
        application_id, email = signing.loads(
            request.GET.get("t", ""), salt="cciw-officers-correct_application", max_age=60 * 60 * 24 * 10
        )  # 10 days
    except signing.BadSignature:
        context["message"] = (
            "The URL was invalid. Please ensure you copied the URL from the email correctly, "
            "or contact the webmaster if you are having difficulties."
        )
    else:
        application = get_object_or_404(Application.objects.filter(id=application_id))
        application.address_email = email
        application.save()
        context["message"] = "Your application form email address has been updated, thanks."
        context["success"] = True

    return TemplateResponse(request, "cciw/officers/email_update.html", context)
