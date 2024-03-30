from typing import Any

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse

from cciw.officers.applications import invitations_for_application
from cciw.officers.email import make_ref_form_url_hash
from cciw.officers.forms import ReferenceForm
from cciw.officers.models import Referee, Reference, empty_reference


def get_initial_reference_form(reference: Reference, referee: Referee, prev_reference: Reference | None, form_class):
    initial_data = initial_reference_form_data(referee, prev_reference)
    if reference is not None:
        # For the case where a Reference has been created (accidentally)
        # by an admin, we need to re-use it, rather than create another.
        if empty_reference(reference):
            # Need to fill data
            for k, v in initial_data.items():
                setattr(reference, k, v)
        form = form_class(instance=reference)
    else:
        form = form_class(initial=initial_data)
    return form


def create_reference(request, referee_id: int, hash: str, prev_ref_id: int | None = None):
    """
    View for allowing referee to submit reference (create the Reference object)
    """
    context: dict[str, Any] = {}
    if hash != make_ref_form_url_hash(referee_id, prev_ref_id):
        context["incorrect_url"] = True
    else:
        referee: Referee = get_object_or_404(Referee.objects.filter(id=referee_id))
        prev_reference = None
        if prev_ref_id is not None:
            prev_reference = get_object_or_404(Reference.objects.filter(id=prev_ref_id))

        if prev_reference is not None:
            context["update"] = True
            context["last_form_date"] = prev_reference.created_on if not prev_reference.inaccurate else None
            context["last_empty"] = empty_reference(prev_reference)

        reference = referee.reference if hasattr(referee, "reference") else None
        relevant_invitations = invitations_for_application(referee.application)
        role_names = sorted(list({i.role.name for i in relevant_invitations if i.role is not None}))
        context["roles"] = role_names

        if reference is not None and not empty_reference(reference):
            # It's possible that empty references have been created in the past,
            # so ensure that these don't stop people filling out form.
            context["already_submitted"] = True
        else:
            if request.method == "POST":
                form = ReferenceForm(request.POST, instance=reference)
                if form.is_valid():
                    form.save(referee)
                    return HttpResponseRedirect(reverse("cciw-officers-create_reference_thanks"))
            else:
                form = get_initial_reference_form(reference, referee, prev_reference, ReferenceForm)
            context["form"] = form
        context["officer"] = referee.application.officer
    return TemplateResponse(request, "cciw/officers/create_reference.html", context)


def create_reference_thanks(request):
    return TemplateResponse(request, "cciw/officers/create_reference_thanks.html", {})


def initial_reference_form_data(referee: Referee, prev_reference: Reference | None):
    """
    Return the initial data to be used for Reference, given the current
    Referee object and the Reference object with data to be copied.
    """
    retval = {}
    if prev_reference is not None:
        # Copy data over
        for f in Reference._meta.fields:
            fname = f.attname
            if fname not in ["id", "created_on"]:
                retval[fname] = getattr(prev_reference, fname)
    retval["referee_name"] = referee.name
    return retval
