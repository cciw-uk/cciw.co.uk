import datetime
import itertools
import operator

from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin import widgets
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.core.validators import email_re
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import wordwrap
from django.views.decorators.cache import never_cache

from cciw.cciwmain import common
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import python_to_json
from cciw.mail.lists import address_for_camp_officers, address_for_camp_slackers
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_txt_filename, thisyears_applications, applications_for_camp, camps_for_application
from cciw.officers import create
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from cciw.officers.email import make_update_email_hash, send_reference_request_email, make_ref_form_url, make_ref_form_url_hash, send_leaders_reference_email, send_nag_by_officer, send_crb_consent_problem_email
from cciw.officers.widgets import ExplicitBooleanFieldSelect
from cciw.officers.models import Application, Reference, ReferenceForm, Invitation, CRBApplication, CRBFormLog
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.officers.references import reference_form_info
from cciw.utils.views import close_window_response
from securedownload.views import access_folder_securely


def _copy_application(application):
    new_obj = Application(id=None)
    for field in Application._meta.fields:
        if field.attname != 'id':
            setattr(new_obj, field.attname, getattr(application, field.attname))
    new_obj.youth_work_declined = None
    new_obj.relevant_illness = None
    new_obj.crime_declaration = None
    new_obj.court_declaration = None
    new_obj.concern_declaration = None
    new_obj.allegation_declaration = None
    new_obj.crb_check_consent = None
    new_obj.finished = False
    new_obj.date_submitted = None
    return new_obj


SECRETARY_GROUP_NAME = 'Secretaries'
LEADER_GROUP_NAME = 'Leaders'

def _is_camp_admin(user):
    """
    Returns True if the user is an admin for any camp, or has rights
    for editing camp/officer/reference/CRB information
    """
    return (user.groups.filter(name=LEADER_GROUP_NAME) |
            user.groups.filter(name=SECRETARY_GROUP_NAME)).exists() \
        or user.camps_as_admin.exists() > 0

camp_admin_required = user_passes_test(_is_camp_admin)


def _is_cciw_secretary(user):
    return user.groups.filter(name=SECRETARY_GROUP_NAME).exists()


def _is_camp_officer(user):
    return user.is_authenticated() and \
        (user.groups.filter(name='Officers') |
         user.groups.filter(name='Leaders')).exists()


def _camps_as_admin_or_leader(user):
    """
    Returns all the camps for which the user is an admin or leader.
    """
    # If the user is am 'admin' for some camps:
    camps = user.camps_as_admin.all()
    # Find the 'Person' object that corresponds to this user
    leaders = list(user.person_set.all())
    # Find the camps for this leader
    # (We could do:
    #    Person.objects.get(user=user.id).camps_as_leader.all(),
    #  but we also must we handle the possibility that two Person
    #  objects have the same User objects, which could happen in the
    #  case where a leader leads by themselves and as part of a couple)
    for leader in leaders:
        camps = camps | leader.camps_as_leader.all()

    return camps.distinct()

def close_window_and_update_ref(ref_id):
    """
    HttpResponse that closes the current window, and updates the reference
    in the parent window. Applies to popup from manage_references view.
    """
    return HttpResponse("""<!DOCTYPE HTML><html><head><title>Close</title><script type="text/javascript">window.opener.refreshReferenceSection(%s); window.close()</script></head><body></body></html>""" % ref_id)


# /officers/
@staff_member_required
@never_cache
def index(request):
    """Displays a list of links/buttons for various actions."""
    user = request.user
    c = {}
    c['thisyear'] = common.get_thisyear()
    if _is_camp_admin(user):
        c['show_leader_links'] = True
        c['show_admin_link'] = True
    if _is_cciw_secretary(user):
        c['show_secretary_links'] = True
        c['show_admin_link'] = True

    return render(request, 'cciw/officers/index.html', c)


@staff_member_required
@camp_admin_required
def leaders_index(request):
    """Displays a list of links for actions for leaders"""
    user = request.user
    c = {}
    thisyear = common.get_thisyear()
    c['current_camps'] = _camps_as_admin_or_leader(user).filter(year=thisyear)
    c['old_camps'] = _camps_as_admin_or_leader(user).filter(year__lt=thisyear)
    c['statsyears'] = [thisyear, thisyear - 1, thisyear - 2]

    return render(request, 'cciw/officers/leaders_index.html', c)


@staff_member_required
@never_cache
def applications(request):
    """Displays a list of tasks related to applications."""
    user = request.user
    c = {}

    finished_applications = user.application_set\
        .filter(finished=True)\
        .order_by('-date_submitted')
    # A NULL date_submitted means they never pressed save, so there is no point
    # re-editing, so we ignore them.
    unfinished_applications = user.application_set\
        .filter(finished=False)\
        .exclude(date_submitted__isnull=True)\
        .order_by('-date_submitted')
    has_thisyears_app = thisyears_applications(user).exists()
    has_completed_app = thisyears_applications(user).filter(finished=True).exists()

    c['finished_applications'] = finished_applications
    c['unfinished_applications'] = unfinished_applications
    c['has_thisyears_app'] = has_thisyears_app
    c['has_completed_app'] = has_completed_app

    if not has_completed_app and unfinished_applications and request.POST.has_key('edit'):
        # Edit existing application.
        # It should now only be possible for there to be one unfinished
        # application, so we just continue with the most recent.
        return HttpResponseRedirect(
            reverse("admin:officers_application_change",
                    args=(unfinished_applications[0].id,)))
    elif not has_thisyears_app and request.POST.has_key('new'):
        # Create new application based on old one
        if finished_applications:
            new_obj = _copy_application(finished_applications[0])
            new_obj.save()
        else:
            new_obj = Application.objects.create(officer=user,
                                                 full_name=u"%s %s" % (user.first_name, user.last_name))

        return HttpResponseRedirect('/admin/officers/application/%s/' %
                                    new_obj.id)

    return render(request, 'cciw/officers/applications.html', c)


@staff_member_required
def view_application(request):
    try:
        application_id = int(request.POST['application'])
    except:
        raise Http404

    try:
        app = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        raise Http404

    if app.officer_id != request.user.id and \
            not _is_camp_admin(request.user):
        raise PermissionDenied

    # NB, this is is called by both normal users and leaders.
    # In the latter case, request.user != app.officer

    format = request.POST.get('format', '')
    if format == 'txt':
        resp = HttpResponse(application_to_text(app), mimetype="text/plain")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_txt_filename(app)
        return resp
    elif format == 'rtf':
        resp = HttpResponse(application_to_rtf(app), mimetype="text/rtf")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_rtf_filename(app)
        return resp
    elif format == 'send':
        application_text = application_to_text(app)
        application_rtf = application_to_rtf(app)
        rtf_attachment = (application_rtf_filename(app),
                          application_rtf, 'text/rtf')

        msg = \
u"""Dear %s,

Please find attached a copy of the application you requested
 -- in plain text below and an RTF version attached.

""" % request.user.first_name
        msg = msg + application_text

        send_mail_with_attachments("Copy of CCIW application - %s" % app.full_name,
                                   msg, settings.SERVER_EMAIL,
                                   [formatted_email(request.user)],
                                   attachments=[rtf_attachment])
        messages.info(request, "E-mail sent.")

        # Redirect back where we came from
        return HttpResponseRedirect(request.POST.get('to', '/officers/'))

    else:
        raise Http404

    return resp


def _thisyears_camp_for_leader(user):
    leaders = list(user.person_set.all())
    try:
        return leaders[0].camps_as_leader.get(year=common.get_thisyear(),
                                              online_applications=True)
    except (ObjectDoesNotExist, IndexError):
        return None


@staff_member_required
@camp_admin_required
@never_cache
def manage_applications(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)
    c = {}
    c['finished_applications'] = applications_for_camp(camp).order_by('officer__first_name', 'officer__last_name')
    c['camp'] = camp

    return render(request, 'cciw/officers/manage_applications.html', c)

def _get_camp_or_404(year, number):
    try:
        return Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist, ValueError:
        raise Http404


def get_previous_references(ref, camp):
    """
    Returns a tuple of:
     (possible previous References ordered by relevance,
      exact match for previous Reference or None if it doesn't exist)
    """
    # Look for ReferenceForms for same officer, within the previous five
    # years.  Don't look for references from this year's
    # application (which will be the other referee).
    cutoffdate = camp.start_date - datetime.timedelta(365*5)
    prev = list(ReferenceForm.objects\
                .filter(reference_info__application__officer=ref.application.officer,
                        reference_info__application__finished=True,
                        reference_info__received=True,
                        date_created__gte=cutoffdate)\
                .exclude(reference_info__application=ref.application)\
                .order_by('-reference_info__application__date_submitted'))

    # Sort by relevance
    def relevance_key(refform):
        # Matching name or e-mail address is better, so has lower value,
        # so it comes first.
        return -(int(refform.reference_info.referee.email==ref.referee.email) +
                 int(refform.reference_info.referee.name ==ref.referee.name))
    prev.sort(key=relevance_key) # sort is stable, so previous sort by date should be kept

    exact = None
    for refform in prev:
        if refform.reference_info.referee == ref.referee:
            exact = refform.reference_info
            break
    return ([rf.reference_info for rf in prev], exact)


@staff_member_required
@camp_admin_required # we don't care which camp they are admin for.
@never_cache
def manage_references(request, year=None, number=None):
    c = {}

    # If ref_id is set, we just want to update part of the page.
    ref_id = request.GET.get('ref_id')

    camp = _get_camp_or_404(year, number)
    c['camp'] = camp

    if ref_id is None:
        apps = applications_for_camp(camp)
        app_ids = [app.id for app in apps]
        # force creation of Reference objects.
        if Reference.objects.filter(application__in=app_ids).count() < len(apps) * 2:
            [a.references for a in apps]

        refinfo = Reference.objects\
            .filter(application__in=app_ids)\
            .order_by('application__officer__first_name', 'application__officer__last_name',
                      'referee_number')

    else:
        refinfo = Reference.objects.filter(pk=ref_id).order_by()

    received = refinfo.filter(received=True)
    requested = refinfo.filter(received=False, requested=True)
    notrequested = refinfo.filter(received=False, requested=False)

    for l in (received, requested, notrequested):
        # decorate each Reference with suggested previous ReferenceForms.
        for curref in l:
            (prev, exact) = get_previous_references(curref, camp)
            if exact is not None:
                curref.previous_reference = exact
            else:
                curref.possible_previous_references = prev

    if ref_id is None:
        c['notrequested'] = notrequested
        c['requested'] = requested
        c['received'] = received
        template_name = 'cciw/officers/manage_references.html'
    else:
        if received:
            c['mode'] = 'received'
            c['ref'] = received[0]
        elif requested:
            c['mode'] = 'requested'
            c['ref'] = requested[0]
        else:
            c['mode'] = 'notrequested'
            c['ref'] = notrequested[0]
        template_name = 'cciw/officers/manage_reference.html'

    return render(request, template_name, c)


class SetEmailForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={'size':'50'}))


class SendMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols':80, 'rows':20}))

    def __init__(self, *args, **kwargs):
        message_info = kwargs.pop('message_info', {})
        self.message_info = message_info
        msg_template = self.get_message_template()
        msg = render_to_string(msg_template, message_info)
        initial = kwargs.pop('initial', {})
        initial['message'] = msg
        kwargs['initial'] = initial
        return super(SendMessageForm, self).__init__(*args, **kwargs)

    def get_message_template(self):
        raise NotImplementedError


class SendReferenceRequestForm(SendMessageForm):

    def get_message_template(self):
        if self.message_info['update']:
            return 'cciw/officers/request_reference_update.txt'
        else:
            return 'cciw/officers/request_reference_new.txt'

    def clean(self):
        cleaned_data = self.cleaned_data
        url = self.message_info['url']
        if url not in cleaned_data.setdefault('message', ''):
            errmsg = "You removed the link %s from the message.  This link is needed for the referee to be able to submit their reference" % url
            self._errors.setdefault('message', self.error_class([])).append(errmsg)
            del cleaned_data['message']
        return cleaned_data


@staff_member_required
@camp_admin_required # we don't care which camp they are admin for.
def request_reference(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)
    try:
        ref_id = int(request.GET.get('ref_id'))
    except ValueError, TypeError:
        raise Http404
    ref = get_object_or_404(Reference.objects.filter(id=ref_id))
    app = ref.application

    if 'manual' in request.GET:
        return manage_reference_manually(request, ref)

    c = {}

    # Need to handle any changes to the referees first, for correctness of what
    # follows
    if request.method == "POST" and 'setemail' in request.POST:
        emailform = SetEmailForm(request.POST)
        if emailform.is_valid():
            app.referees[ref.referee_number-1].email = emailform.cleaned_data['email']
            app.save()
            messages.info(request, "E-mail address updated.")

    # Work out 'old_referee' or 'known_email_address', and the URL to use in the
    # message.
    update = 'update' in request.GET
    if update:
        (possible, exact) = get_previous_references(ref, camp)
        prev_ref_id = int(request.GET['prev_ref_id'])
        if exact is not None:
            # the prev_ref_id must be the same as exact.id by the logic of the
            # buttons available on the manage_references page. If not true, we
            # close the page and update the parent page, in case the parent is
            # out of date.
            if exact.id != prev_ref_id:
                return close_window_and_update_ref(ref_id)
            c['known_email_address'] = True
        else:
            # Get old referee data
            refs = [r for r in possible if r.id == prev_ref_id]
            assert len(refs) == 1
            c['old_referee'] = refs[0].referee
        url = make_ref_form_url(ref.id, prev_ref_id)
    else:
        url = make_ref_form_url(ref.id, None)

    messageform_info = dict(referee=ref.referee,
                            applicant=app.officer,
                            camp=camp,
                            url=url,
                            update=update)
    emailform = None
    messageform = None

    if request.method == 'POST':
        if 'send' in request.POST:
            messageform = SendReferenceRequestForm(request.POST, message_info=messageform_info)
            if messageform.is_valid():
                send_reference_request_email(wordwrap(messageform.cleaned_data['message'], 70), ref)
                ref.requested = True
                ref.log_request_made(request.user, datetime.datetime.now())
                ref.save()
                return close_window_and_update_ref(ref_id)
        elif 'cancel' in request.POST:
            return close_window_response()

    if emailform is None:
        emailform = SetEmailForm(initial={'email': ref.referee.email})
    if messageform is None:
        messageform = SendReferenceRequestForm(message_info=messageform_info)

    if not email_re.match(ref.referee.email.strip()):
        c['bad_email'] = True
    c['is_popup'] = True
    c['already_requested'] = ref.requested
    c['referee'] = ref.referee
    c['app'] = app
    c['is_update'] = update
    c['emailform'] = emailform
    c['messageform'] = messageform
    return render(request, 'cciw/officers/request_reference.html', c)


class SendNagByOfficerForm(SendMessageForm):
    def get_message_template(self):
        return 'cciw/officers/nag_by_officer_email.txt'


@staff_member_required
@camp_admin_required # we don't care which camp they are admin for.
def nag_by_officer(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)
    try:
        ref_id = int(request.GET.get('ref_id'))
    except ValueError, TypeError:
        raise Http404
    ref = get_object_or_404(Reference.objects.filter(id=ref_id))
    app = ref.application
    officer = app.officer

    c = {}
    messageform_info = dict(referee=ref.referee,
                            officer=officer,
                            camp=camp)

    if request.method == 'POST':
        if 'send' in request.POST:
            messageform = SendNagByOfficerForm(request.POST, message_info=messageform_info)
            # It's impossible for the form to be invalid, so assume valid
            messageform.is_valid()
            send_nag_by_officer(wordwrap(messageform.cleaned_data['message'], 70), officer, ref)
            return close_window_response()
        else:
            # cancel
            return close_window_response()

    messageform = SendNagByOfficerForm(message_info=messageform_info)

    c['referee'] = ref.referee
    c['app'] = app
    c['officer'] = officer
    c['messageform'] = messageform
    c['is_popup'] = True
    return render(request, 'cciw/officers/nag_by_officer.html', c)


class ReferenceFormForm(forms.ModelForm):
    class Meta:
        model = ReferenceForm
        fields = ('referee_name',
                  'how_long_known',
                  'capacity_known',
                  'known_offences',
                  'known_offences_details',
                  'capability_children',
                  'character',
                  'concerns',
                  'comments')


normal_textarea = forms.Textarea(attrs={'cols':80, 'rows':10})
small_textarea = forms.Textarea(attrs={'cols':80, 'rows':5})
ReferenceFormForm.base_fields['capacity_known'].widget = small_textarea
ReferenceFormForm.base_fields['known_offences'].widget = ExplicitBooleanFieldSelect()
ReferenceFormForm.base_fields['known_offences_details'].widget = normal_textarea
ReferenceFormForm.base_fields['capability_children'].widget = normal_textarea
ReferenceFormForm.base_fields['character'].widget = normal_textarea
ReferenceFormForm.base_fields['concerns'].widget = normal_textarea
ReferenceFormForm.base_fields['comments'].widget = normal_textarea


# I have models called Reference and ReferenceForm.  What do I call a Form
# for model Reference? I'm a loser...
class ReferenceEditForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = ('requested', 'received', 'comments')


def manage_reference_manually(request, ref):
    """
    Returns page for manually editing Reference and ReferenceForm details.
    """
    c = {}
    c['ref'] = ref
    c['referee'] = ref.referee
    c['officer'] = ref.application.officer
    if request.method == 'POST':
        if 'save' in request.POST:
            form = ReferenceEditForm(request.POST, instance=ref)
            if form.is_valid():
                form.save()
                return close_window_and_update_ref(ref.id)
        else:
            return close_window_response()
    else:
        form = ReferenceEditForm(instance=ref)
    c['form'] = form
    c['is_popup'] = True
    return render(request, "cciw/officers/manage_reference_manual.html", c)


@staff_member_required
@camp_admin_required # we don't care which camp they are admin for.
def edit_reference_form_manually(request, ref_id=None):
    """
    Create ReferenceForm if necessary, then launch normal admin popup for
    editing it.
    """
    ref = get_object_or_404(Reference.objects.filter(id=int(ref_id)))
    if ref.reference_form is None:
        # Create it
        ReferenceForm.objects.create(reference_info=ref,
                                     referee_name=ref.referee.name,
                                     date_created=datetime.date.today(),
                                     known_offences=False)
    return HttpResponseRedirect(reverse("admin:officers_referenceform_change",
                                        args=(ref.reference_form.id,)) + \
                                "?_popup=1")


def initial_reference_form_data(ref, prev_ref_form):
    """
    Return the initial data to be used for ReferenceFormForm, given the current
    Reference objects and the ReferenceForm object with data to be copied.
    """
    retval =  {}
    if prev_ref_form is not None:
        # Copy data over
        for f in ReferenceFormForm._meta.fields:
            retval[f] = getattr(prev_ref_form, f)
    retval['referee_name'] = ref.referee.name
    retval.pop('date_created', None)
    return retval


def empty_reference(ref_form):
    return ref_form.how_long_known.strip() == ""


def create_reference_form(request, ref_id="", prev_ref_id="", hash=""):
    """
    View for allowing referee to submit reference (create the ReferenceForm object)
    """
    c = {}
    if hash != make_ref_form_url_hash(ref_id, prev_ref_id):
        c['incorrect_url'] = True
    else:
        ref = get_object_or_404(Reference.objects.filter(id=int(ref_id)))
        prev_ref = None
        if prev_ref_id != "":
            prev_ref = get_object_or_404(Reference.objects.filter(id=int(prev_ref_id)))

        if prev_ref is not None:
            prev_ref_form = prev_ref.reference_form
            c['update'] = True
            c['last_form_date'] = prev_ref_form.date_created
        else:
            prev_ref_form = None

        ref_form = ref.reference_form
        if ref_form is not None:
            # For the case where a ReferenceForm has been created (accidentally)
            # by an admin, we need to re-use it, rather than create another.
            instance = ref_form
        else:
            instance = None

        if ref_form is not None and ref.received and not empty_reference(ref_form):
            # It's possible, if an admin has done 'Manage reference manually'
            # and clicked "Create/edit reference form" but then cancelled, that
            # the ReferenceForm will exist but be empty.  So we check both that
            # it exists and that the 'ref.received' is True, otherwise a referee
            # will be unable to fill out the form.
            c['already_submitted'] = True
        else:
            if request.method == 'POST':
                form = ReferenceFormForm(request.POST, instance=instance)
                if form.is_valid():
                    obj = form.save(commit=False)
                    obj.reference_info = ref
                    obj.date_created = datetime.date.today()
                    obj.save()
                    ref.received = True
                    ref.comments = ref.comments + \
                                   ("\nReference received via online system on %s\n" % \
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    ref.save()
                    # Send e-mails
                    send_leaders_reference_email(obj)
                    return HttpResponseRedirect(reverse('cciw.officers.views.create_reference_thanks'))
            else:
                initial_data = initial_reference_form_data(ref, prev_ref_form)
                if instance is not None:
                    if empty_reference(instance):
                        # Need to fill data
                        for k, v in initial_data.items():
                            setattr(instance, k, v)
                    form = ReferenceFormForm(instance=instance)
                else:
                    form = ReferenceFormForm(initial=initial_data)
            c['form'] = form
        c['officer'] = ref.application.officer
    return render(request, 'cciw/officers/create_reference.html', c)


def create_reference_thanks(request):
    return render(request, 'cciw/officers/create_reference_thanks.html', {})


@staff_member_required
@camp_admin_required
def view_reference(request, ref_id=None):
    ref = get_object_or_404(Reference.objects.filter(id=ref_id))
    ref_form = ref.reference_form
    c = {}
    if ref_form is not None:
        c['refform'] = ref_form
        c['info'] = reference_form_info(ref_form)
    c['ref'] = ref
    c['officer'] = ref.application.officer
    c['referee'] = ref.referee
    c['is_popup'] = True

    return render(request, "cciw/officers/view_reference_form.html", c)


@staff_member_required
@camp_admin_required
def officer_list(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = {}
    c['camp'] = camp
    # Make sure these queries come after the above data modification
    invitation_list = camp.invitation_set.all()
    officer_list_ids = set(i.officer_id for i in invitation_list)
    c['invitations'] = invitation_list
    c['officers_noapplicationform'] = camp_slacker_list(camp)
    c['address_all'] = address_for_camp_officers(camp)
    c['address_noapplicationform'] = address_for_camp_slackers(camp)

    # List for select
    available_officers = list(User.objects.filter(is_staff=True).order_by('first_name', 'last_name', 'email'))
    # decorate with info about previous camp
    prev_camp = camp.previous_camp
    if prev_camp is not None:
        prev_officer_list_ids = set(u.id for u in prev_camp.officers.all())
        for u in available_officers:
            if u.id in prev_officer_list_ids:
                u.on_previous_camp = True
    # Filter out officers who are already chosen for this camp.
    # Since the total number of officers >> officers chosen for a camp
    # there is no need to do this filtering in the database.
    available_officers = [u for u in available_officers if u.id not in officer_list_ids]
    available_officers.sort(key=lambda u: not getattr(u, 'on_previous_camp', False))
    c['available_officers'] = available_officers

    # Different templates allow us to render just parts of the page, for AJAX calls
    if 'sections' in request.GET:
        tnames = [("chosen", "cciw/officers/officer_list_table_editable.html"),
                  ("available", "cciw/officers/officer_list_available.html"),
                  ("noapplicationform", "cciw/officers/officer_list_noapplicationform.html")]
        retval = {}
        for section, tname in tnames:
            retval[section] = render_to_string(tname, context_instance=RequestContext(request, c))
        return HttpResponse(python_to_json(retval),
                            mimetype="text/javascript")
    else:
        return render(request, "cciw/officers/officer_list.html", c)


@staff_member_required
@camp_admin_required
@json_response
def remove_officer(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)
    officer_id = request.POST['officer_id']
    Invitation.objects.filter(camp=camp.id, officer=int(officer_id)).delete()
    return {'status':'success'}


@staff_member_required
@camp_admin_required
@json_response
def add_officers(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)
    for officer_id in request.POST['officer_ids'].split(','):
        try:
            i = Invitation.objects.get(camp=camp, officer=User.objects.get(id=int(officer_id)))
        except Invitation.DoesNotExist:
            i = Invitation.objects.create(camp=camp,
                                          officer=User.objects.get(id=int(officer_id)),
                                          date_added=datetime.date.today())
    return {'status':'success'}


@staff_member_required
@camp_admin_required
@json_response
def officer_details(request):
    # We use POST here, to avoid information leaks associated with JSON over GET
    # by 3rd party <script> tags.

    # We base things on the user id and camp id, rather than on invitation id,
    # since it is much less likely that camps and users will be deleted (they
    # never will be in practice), but an invitation can be deleted, potentially
    # leading to overwriting of the wrong data if invitation ids are re-used in
    # the database
    user = User.objects.get(pk=int(request.POST['officer_id']))
    invitation = user.invitation_set.get(camp=int(request.POST['camp_id']))
    return {'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'notes': invitation.notes,
            'id': user.id,
            }


@staff_member_required
@camp_admin_required
@json_response
def update_officer(request):
    User.objects.filter(pk=int(request.POST['officer_id'])).update(first_name=request.POST['first_name'].strip(),
                                                                   last_name=request.POST['last_name'].strip(),
                                                                   email=request.POST['email'].strip()
                                                                   )
    Invitation.objects.filter(camp=int(request.POST['camp_id']),
                              officer=int(request.POST['officer_id'])).update(notes=request.POST['notes'].strip())
    return {'status':'success'}


def update_email(request, username=''):
    c = {}
    u = get_object_or_404(User.objects.filter(username=username))
    email = request.GET.get('email', '')
    hash = request.GET.get('hash', '')

    if email == u.email:
        c['message'] = "The e-mail address has already been updated, thanks."
    else:
        if make_update_email_hash(u.email, email) != hash:
            c['message'] = "The URL was invalid. Please ensure you copied the URL from the e-mail correctly"
        else:
            c['message'] = "Your e-mail address has been updated, thanks."
            c['success'] = True
            u.email = email
            u.save()

    return render(request, 'cciw/officers/email_update.html', c)


class StripStringsMixin(object):
    def clean(self):
        for field,value in self.cleaned_data.items():
            if isinstance(value, basestring):
                self.cleaned_data[field] = value.strip()
        return self.cleaned_data


class BaseForm(StripStringsMixin, forms.Form):
    pass


class CreateOfficerForm(BaseForm):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()

    def save(self):
        return create.create_officer(None, self.cleaned_data['first_name'],
                                     self.cleaned_data['last_name'],
                                     self.cleaned_data['email'])


@staff_member_required
@camp_admin_required
def create_officer(request):
    allow_confirm = True
    duplicate_message = ""
    existing_users = None
    message = ""
    if request.method == "POST":
        form = CreateOfficerForm(request.POST)
        process_form = False
        if form.is_valid():
            if "add" in request.POST:
                same_name_users = User.objects.filter(first_name__iexact=form.cleaned_data['first_name'],
                                                      last_name__iexact=form.cleaned_data['last_name'])
                same_email_users = User.objects.filter(email__iexact=form.cleaned_data['email'])
                same_user = same_name_users & same_email_users
                if same_user.exists():
                    allow_confirm = False
                    duplicate_message = "A user with that name and e-mail address already exists. You can change the details above and try again."
                elif len(same_name_users) > 0:
                    existing_users = same_name_users
                    if len(existing_users) == 1:
                        duplicate_message = "A user with that first name and last name " + \
                                            "already exists:"
                    else:
                        duplicate_message = ("%d users with that first name and last name " +
                                            "already exist:") % len(existing_users)
                elif len(same_email_users):
                    existing_users = same_email_users
                    if len(existing_users) == 1:
                        duplicate_message = "A user with that e-mail address already exists:"
                    else:
                        duplicate_message = "%d users with that e-mail address already exist:"\
                                            % len(existing_users)
                else:
                    process_form = True

            elif "confirm" in request.POST:
                process_form = True

            if process_form:
                try:
                    u = form.save()
                    form = CreateOfficerForm()
                    messages.info(request, "Officer %s has been added and e-mailed.  You can add another if required, or close this popup to continue." % u.username)
                    camp_id = request.GET.get('camp_id')
                    if camp_id is not None:
                        Invitation.objects.get_or_create(camp=Camp.objects.get(id=camp_id), officer=u)
                except create.EmailError:
                    messages.error(request, "Due to a problem sending e-mail, the officer has not been added to the system.  Please try again later.")

    else:
        form = CreateOfficerForm()

    c = {'form': form,
         'duplicate_message': duplicate_message,
         'existing_users': existing_users,
         'allow_confirm': allow_confirm,
         'message': message,
         'is_popup': True,
         }
    return render(request, 'cciw/officers/create_officer.html', c)


@staff_member_required
@camp_admin_required
@json_response
def resend_email(request):
    u = User.objects.get(pk=int(request.POST['officer_id']))
    password = User.objects.make_random_password()
    u.set_password(password)
    u.save()
    create.email_officer(u.username, u.first_name, u.email, password, is_leader=False, update=True)
    return {'status':'success'}


officer_files = access_folder_securely("officers",
                                       lambda request: _is_camp_officer(request.user))


def date_to_js_ts(d):
    """
    Converts a date object to the timestamp required by the flot library
    """
    return int(d.strftime('%s'))*1000


@staff_member_required
@camp_admin_required
def stats(request, year=None):
    year = int(year)
    stats = []
    camps = list(Camp.objects.filter(year=year).order_by('number'))
    if len(camps) == 0:
        raise Http404
    for camp in camps:
        stat = {}
        # For efficiency, we are careful about what DB queries we do and what is
        # done in Python.
        stat['camp'] = camp

        invited_officers = list(camp.invitation_set.all().order_by('date_added').values_list('officer_id', 'date_added'))
        application_forms = list(applications_for_camp(camp).order_by('date_submitted').values_list('id', 'date_submitted'))

        officer_ids = [o[0] for o in invited_officers]
        officer_dates = [o[1] for o in invited_officers]
        app_ids = [a[0] for a in application_forms]
        app_dates = [a[1] for a in application_forms]
        ref_dates = list(ReferenceForm.objects.filter(reference_info__application__in=app_ids).order_by('date_created').values_list('date_created', flat=True))
        all_crb_info = list(CRBApplication.objects.filter(officer__in=officer_ids).order_by('completed').values_list('officer_id', 'completed'))
        # We duplicate logic from CRBApplication.get_for_camp here to avoid
        # duplicating queries
        valid_crb_info = [(off_id, d) for off_id, d in all_crb_info
                          if d >= camp.start_date - datetime.timedelta(settings.CRB_VALID_FOR)]
        # Make a plot by going through each day in the year before the camp and
        # incrementing a counter. This requires the data to be sorted already,
        # as above.
        graph_start_date = camp.start_date - datetime.timedelta(365)
        graph_end_date = min(camp.start_date, datetime.date.today())
        a = 0 # applications
        r = 0 # references
        o = 0 # officers
        v_idx = 0 # valid CRBs - index into valid_crb_info
        c_idx = 0 # CRBs       - index into all_crb_info
        v_tot = 0 #            - total for valid CRBs
        c_tot = 0 #            - total for all CRBs
        app_dates_data = []
        ref_dates_data = []
        officer_dates_data = []
        all_crb_dates_data = []
        _all_crb_seen_officers = set()
        valid_crb_dates_data = []
        _valid_crb_seen_officers = set()
        d = graph_start_date
        while d <= graph_end_date:
            # Application forms
            while a < len(app_dates) and app_dates[a] <= d:
                a += 1
            # References
            while r < len(ref_dates) and ref_dates[r] <= d:
                r += 1
            # Officers
            while o < len(officer_dates) and officer_dates[o] <= d:
                o += 1

            # CRBs: there can be multiple CRBs for each officer. If we've
            # already seen one, we don't increase the count.

            # Valid CRBs
            while v_idx < len(valid_crb_info) and valid_crb_info[v_idx][1] <= d:
                off_id = valid_crb_info[v_idx][0]
                v_idx += 1
                if off_id not in _valid_crb_seen_officers:
                    v_tot += 1
                    _valid_crb_seen_officers.add(off_id)
            # CRBs
            while c_idx < len(all_crb_info) and all_crb_info[c_idx][1] <= d:
                off_id = all_crb_info[c_idx][0]
                c_idx += 1
                if off_id not in _all_crb_seen_officers:
                    c_tot += 1
                    _all_crb_seen_officers.add(off_id)
            # Formats are those needed by 'flot' library
            ts = date_to_js_ts(d)
            app_dates_data.append([ts, a])
            ref_dates_data.append([ts, r/2.0])
            officer_dates_data.append([ts, o])
            all_crb_dates_data.append([ts, c_tot])
            valid_crb_dates_data.append([ts, v_tot])
            d = d + datetime.timedelta(1)
        stat['application_dates_data'] = app_dates_data
        stat['reference_dates_data'] = ref_dates_data
        stat['all_crb_dates_data'] = all_crb_dates_data
        stat['valid_crb_dates_data'] = valid_crb_dates_data
        # Project officer list graphs at either end, to make the graph stretch that far.
        officer_dates_data.insert(0, [date_to_js_ts(graph_start_date), 0])
        officer_dates_data.append([date_to_js_ts(camp.start_date), len(officer_ids)])
        stat['officer_list_data'] = officer_dates_data
        stats.append(stat)


    d = {}
    d['stats'] = stats
    d['year'] = year
    return render(request, 'cciw/officers/stats.html', d)


@staff_member_required
@camp_admin_required
def manage_crbs(request, year=None):
    year = int(year)
    # We need a lot of information. Try to get it in a few up-front queries
    camps = list(Camp.objects.filter(year=year).order_by('number'))
    if len(camps) == 0:
        raise Http404
    # Selected camps:
    # We need to support URLs that indicate which camp to select, so we
    # can permalink nicely.
    selected_camp_numbers = None
    if 'camp' in request.GET:
        try:
            selected_camp_numbers = set(map(int, request.GET.getlist('camp')))
        except ValueError:
            pass
    if not selected_camp_numbers: # empty or None
        # Assume all, because having none is never useful
        selected_camp_numbers = set([c.number for c in camps])

    # We need all the officers, and we need to know which camp(s) they belong
    # to. Even if we have only selected one camp, it might be nice to know if
    # they are on other camps. So we get data for all camps, and filter later.
    # We also want to be able to filtering by javascript in the frontend.
    camps_officers = [[i.officer for i in c.invitation_set.all()] for c in camps]
    all_officers = reduce(operator.or_, map(set, camps_officers))
    all_officers = sorted(all_officers, key=lambda o: (o.first_name, o.last_name))
    apps = list(reduce(operator.or_, map(applications_for_camp, camps)))
    valid_crb_officer_ids = set(reduce(operator.or_, map(CRBApplication.objects.get_for_camp, camps)).values_list('officer_id', flat=True))
    all_crb_officer_ids = set(CRBApplication.objects.values_list('officer_id', flat=True))
    # CRB forms sent: set cutoff to a year before now, on the basis that
    # anything more than that will have been lost, and we don't want to load
    # everything into membery.
    crb_forms_sent = list(CRBFormLog.objects.filter(sent__gt=datetime.datetime.now() - datetime.timedelta(365)).order_by('sent'))
    # Work out, without doing any more queries:
    #   which camps each officer is on
    #   if they have an application form
    #   if they have an up to date CRB
    #   when the last CRB form was sent to officer
    officer_ids = dict([(camp.id, set([o.id for o in officers]))
                        for camp, officers in zip(camps, camps_officers)])
    officer_apps = dict([(a.officer_id, a) for a in apps])
    # NB: order_by('sent') above means that requests sent later will overwrite
    # those sent earlier in the following dictionary
    crb_forms_sent_for_officers = dict([(f.officer_id, f.sent) for f in crb_forms_sent])

    for o in all_officers:
        o.temp = {}
        officer_camps = []
        selected = False
        for c in camps:
            if o.id in officer_ids[c.id]:
                officer_camps.append(c)
                if c.number in selected_camp_numbers:
                    selected = True
        app = officer_apps.get(o.id, None)
        o.temp['camps'] = officer_camps
        o.temp['selected'] = selected
        o.temp['has_application_form'] = app is not None
        o.temp['application_id'] = app.id if app is not None else None
        o.temp['has_crb'] = o.id in all_crb_officer_ids
        o.temp['has_valid_crb'] = o.id in valid_crb_officer_ids
        o.temp['last_crb_form_sent'] = crb_forms_sent_for_officers.get(o.id, None)
        o.temp['address'] = app.one_line_address if app is not None else ""
        o.temp['crb_check_consent'] = app.crb_check_consent if app is not None else False

    c = {'all_officers': all_officers,
         'camps': camps,
         'selected_camps': selected_camp_numbers,
         'year':year}
    return render(request, 'cciw/officers/manage_crbs.html', c)


@staff_member_required
@camp_admin_required
@json_response
def mark_crb_sent(request):
    officer_id = int(request.POST['officer_id'])
    officer = User.objects.get(id=officer_id)
    c = CRBFormLog.objects.create(officer=officer,
                                  sent=datetime.datetime.now())
    return {'status':'success',
            'crbFormLogId': str(c.id)
            }


@staff_member_required
@camp_admin_required
@json_response
def undo_mark_crb_sent(request):
    crbformlog_id = int(request.POST['crbformlog_id'])
    c = CRBFormLog.objects.filter(id=crbformlog_id).delete()
    return {'status':'success'}


class CrbConsentProblemForm(SendMessageForm):
    def get_message_template(self):
        return 'cciw/officers/crb_consent_problem_email.txt'


@staff_member_required
@camp_admin_required
def crb_consent_problem(request):
    try:
        app_id = int(request.GET.get('application_id'))
    except ValueError, TypeError:
        raise Http404
    app = get_object_or_404(Application.objects.filter(id=app_id))
    officer = app.officer
    camps = camps_for_application(app)

    c = {}
    messageform_info = dict(application=app,
                            officer=officer,
                            camps=camps,
                            sender=request.user)

    if request.method == 'POST':
        if 'send' in request.POST:
            messageform = CrbConsentProblemForm(request.POST, message_info=messageform_info)
            # It's impossible for the form to be invalid, so assume valid
            messageform.is_valid()
            send_crb_consent_problem_email(wordwrap(messageform.cleaned_data['message'], 70), officer, camps)
            return close_window_response()
        else:
            # cancel
            return close_window_response()

    messageform = CrbConsentProblemForm(message_info=messageform_info)

    c['messageform'] = messageform
    c['officer'] = officer
    c['is_popup'] = True
    return render(request, 'cciw/officers/crb_consent_problem.html', c)
