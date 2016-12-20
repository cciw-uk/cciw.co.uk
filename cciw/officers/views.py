# -*- coding: utf-8 -*-

import operator
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import reduce
from urllib.parse import urlparse

import pandas_highcharts.core
from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.db.models import Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import wordwrap
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache

from cciw.auth import (is_booking_secretary, is_camp_admin, is_camp_officer, is_cciw_secretary, is_committee_member,
                       is_wiki_user)
from cciw.bookings.models import Booking
from cciw.bookings.stats import get_booking_ages_stats, get_booking_progress_stats, get_booking_summary_stats
from cciw.bookings.utils import (addresses_for_mailing_list, camp_bookings_to_spreadsheet,
                                 camp_sharable_transport_details_to_spreadsheet, payments_to_spreadsheet,
                                 year_bookings_to_spreadsheet)
from cciw.cciwmain import common
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import is_valid_email, python_to_json
from cciw.mail.lists import address_for_camp_officers, address_for_camp_slackers
from cciw.utils.views import close_window_response, get_spreadsheet_formatter, user_passes_test_improved
from securedownload.views import access_folder_securely

from . import create
from .applications import (application_rtf_filename, application_to_rtf, application_to_text, application_txt_filename,
                           applications_for_camp, camps_for_application, thisyears_applications)
from .email import (make_ref_form_url, make_ref_form_url_hash, send_crb_consent_problem_email, send_nag_by_officer,
                    send_reference_request_email)
from .email_utils import formatted_email, send_mail_with_attachments
from .forms import (AdminReferenceForm, CrbConsentProblemForm, CreateOfficerForm, ReferenceForm,
                    SendNagByOfficerForm, SendReferenceRequestForm, SetEmailForm, UpdateOfficerForm)
from .models import (Application, CRBApplication, CRBFormLog, Invitation, Referee, Reference, ReferenceAction,
                     empty_reference)
from .stats import get_camp_officer_stats, get_camp_officer_stats_trend
from .utils import camp_serious_slacker_list, camp_slacker_list, officer_data_to_spreadsheet

User = get_user_model()

EXPORT_PAYMENT_DATE_FORMAT = '%Y-%m-%d'


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
    new_obj.save()

    for old_ref, new_ref in zip(application.referees, new_obj.referees):
        for f in ['name', 'address', 'tel', 'mobile', 'email']:
            setattr(new_ref, f, getattr(old_ref, f))
        new_ref.save()

    for q in application.qualifications.all():
        new_q = q.copy(application=new_obj)
        new_q.save()

    return new_obj


def any_passes(*funcs):
    def func(*args, **kwargs):
        for f in funcs:
            if f(*args, **kwargs):
                return True
        return False
    return func

camp_admin_required = user_passes_test_improved(is_camp_admin)
booking_secretary_required = user_passes_test_improved(is_booking_secretary)
cciw_secretary_required = user_passes_test_improved(is_cciw_secretary)
cciw_secretary_or_booking_secretary_required = user_passes_test_improved(any_passes(is_booking_secretary, is_cciw_secretary))
secretary_or_committee_required = user_passes_test_improved(any_passes(is_booking_secretary, is_cciw_secretary, is_committee_member))


def close_window_and_update_referee(ref_id):
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

    # Handle redirects, since this page is LOGIN_URL
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')
    if redirect_to:
        netloc = urlparse(redirect_to)[1]
        # Heavier security check -- don't allow redirection to a different
        # host.
        if netloc == '' or netloc == request.get_host():
            return HttpResponseRedirect(redirect_to)

    user = request.user
    c = {}
    c['thisyear'] = common.get_thisyear()
    c['lastyear'] = c['thisyear'] - 1
    if is_camp_admin(user):
        c['show_leader_links'] = True
        c['show_admin_link'] = True
    if is_cciw_secretary(user):
        c['show_secretary_links'] = True
        c['show_admin_link'] = True
    if is_booking_secretary(user):
        c['show_booking_secretary_links'] = True
    if is_committee_member(user) or is_booking_secretary(user):
        c['show_secretary_and_committee_links'] = True
        most_recent_booking_year = Booking.objects.most_recent_booking_year()
        if most_recent_booking_year is not None:
            c['booking_stats_end_year'] = most_recent_booking_year
            c['booking_stats_start_year'] = most_recent_booking_year - 3

    return render(request, 'cciw/officers/index.html', c)


@staff_member_required
@camp_admin_required
def leaders_index(request):
    """Displays a list of links for actions for leaders"""
    user = request.user
    ctx = {}
    thisyear = common.get_thisyear()

    show_all = 'show_all' in request.GET
    if show_all:
        camps = list(Camp.objects.all())
    else:
        camps = user.camps_as_admin_or_leader
    ctx['current_camps'] = [c for c in camps
                            if c.year == thisyear]
    ctx['old_camps'] = [c for c in camps
                        if c.year < thisyear]
    last_existing_year = Camp.objects.order_by('-year')[0].year
    ctx['statsyears'] = list(range(last_existing_year, last_existing_year - 3, -1))
    ctx['stats_end_year'] = last_existing_year
    ctx['stats_start_year'] = 2006  # first year this feature existed
    ctx['show_all'] = show_all

    return render(request, 'cciw/officers/leaders_index.html', ctx)


@staff_member_required
@never_cache
def applications(request):
    """Displays a list of tasks related to applications."""
    user = request.user
    c = {
        'camps': [i.camp for i in user.invitations.filter(camp__year=common.get_thisyear())]
    }

    finished_applications = (user.applications
                             .filter(finished=True)
                             .order_by('-date_submitted'))
    # A NULL date_submitted means they never pressed save, so there is no point
    # re-editing, so we ignore them.
    unfinished_applications = (user.applications
                               .filter(finished=False)
                               .exclude(date_submitted__isnull=True)
                               .order_by('-date_submitted'))
    has_thisyears_app = thisyears_applications(user).exists()
    has_completed_app = thisyears_applications(user).filter(finished=True).exists()

    c['finished_applications'] = finished_applications
    c['unfinished_applications'] = unfinished_applications
    c['has_thisyears_app'] = has_thisyears_app
    c['has_completed_app'] = has_completed_app

    if not has_completed_app and unfinished_applications and 'edit' in request.POST:
        # Edit existing application.
        # It should now only be possible for there to be one unfinished
        # application, so we just continue with the most recent.
        return HttpResponseRedirect(
            reverse("admin:officers_application_change",
                    args=(unfinished_applications[0].id,)))
    elif not has_thisyears_app and 'new' in request.POST:
        # Create new application based on old one
        if finished_applications:
            new_obj = _copy_application(finished_applications[0])
        else:
            new_obj = Application.objects.create(officer=user,
                                                 full_name="%s %s" % (user.first_name, user.last_name))

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
            not is_camp_admin(request.user):
        raise PermissionDenied

    # NB, this is is called by both normal users and leaders.
    # In the latter case, request.user != app.officer

    format = request.POST.get('format', '')
    if format == 'txt':
        resp = HttpResponse(application_to_text(app), content_type="text/plain")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_txt_filename(app)
        return resp
    elif format == 'rtf':
        resp = HttpResponse(application_to_rtf(app), content_type="text/rtf")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_rtf_filename(app)
        return resp
    elif format == 'send':
        application_text = application_to_text(app)
        application_rtf = application_to_rtf(app)
        rtf_attachment = (application_rtf_filename(app),
                          application_rtf, 'text/rtf')

        msg = ("""Dear %s,

Please find attached a copy of the application you requested
 -- in plain text below and an RTF version attached.

""" % request.user.first_name)
        msg = msg + application_text

        send_mail_with_attachments("Copy of CCIW application - %s" % app.full_name,
                                   msg, settings.SERVER_EMAIL,
                                   [formatted_email(request.user)],
                                   attachments=[rtf_attachment])
        messages.info(request, "Email sent.")

        # Redirect back where we came from
        return HttpResponseRedirect(request.POST.get('to', '/officers/'))

    else:
        raise Http404

    return resp


def _thisyears_camp_for_leader(user):
    leaders = list(user.people.all())
    try:
        return leaders[0].camps_as_leader.get(year=common.get_thisyear())
    except (ObjectDoesNotExist, IndexError):
        return None


@staff_member_required
@camp_admin_required
@never_cache
def manage_applications(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    c = {}
    c['finished_applications'] = applications_for_camp(camp).order_by('officer__first_name', 'officer__last_name')
    c['camp'] = camp

    return render(request, 'cciw/officers/manage_applications.html', c)


def _get_camp_or_404(year, slug):
    try:
        return Camp.objects.get(year=int(year), camp_name__slug=slug)
    except (Camp.DoesNotExist, ValueError):
        raise Http404


TITLES = ["dr", "rev", "reverend", "pastor", "mr", "ms", "mrs", "prof"]


def normalized_name(name):
    # See also application_form.js
    first_word = name.strip().split(' ')[0].lower().replace('.', '')
    if first_word in TITLES:
        name = name[len(first_word):].strip('.').strip()
    return name


def close_enough_referee_match(referee1, referee2):
    if (normalized_name(referee1.name).lower() == normalized_name(referee2.name).lower() and
            referee1.email.lower() == referee2.email.lower()):
        return True

    return False


def add_previous_references(referee):
    """
    Adds the attributes:
    - 'previous_reference' (which is None if no exact match
    - 'possible_previous_references' (list ordered by relevance)
    """
    # Look for References for same officer, within the previous five
    # years.  Don't look for references from this year's
    # application (which will be the other referee).
    cutoffdate = referee.application.date_submitted - timedelta(365 * 5)
    prev = list(Reference.objects
                .filter(referee__application__officer=referee.application.officer,
                        referee__application__finished=True,
                        date_created__gte=cutoffdate)
                .select_related('referee__application')
                .exclude(referee__application=referee.application)
                .order_by('-referee__application__date_submitted'))

    # Sort by relevance
    def relevance_key(reference):
        # Matching name or email address is better, so has lower value,
        # so it comes first.
        return -(int(reference.referee.email.lower() == referee.email.lower()) +
                 int(reference.referee.name.lower() == referee.name.lower()))
    prev.sort(key=relevance_key)  # sort is stable, so previous sort by date should be kept

    exact = None
    for reference in prev:
        if close_enough_referee_match(reference.referee, referee):
            exact = reference
            break
    referee.previous_reference = exact
    referee.possible_previous_references = [] if exact else prev


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
@never_cache
def manage_references(request, year=None, slug=None):
    c = {}

    # If referee_id is set, we just want to update part of the page.
    referee_id = request.GET.get('referee_id')
    officer = None
    officer_id = request.GET.get('officer_id')
    if officer_id is not None:
        try:
            officer = User.objects.get(id=int(officer_id))
        except (ValueError, User.DoesNotExist):
            raise Http404

    c['officer'] = officer
    camp = _get_camp_or_404(year, slug)
    c['camp'] = camp

    if referee_id is None:
        apps = applications_for_camp(camp, officer_ids=[officer_id] if officer is not None else None)
        app_ids = [app.id for app in apps]
        referees = (Referee.objects
                    .filter(application__in=app_ids)
                    .order_by('application__officer__first_name',
                              'application__officer__last_name',
                              'referee_number')
                    )
    else:
        referees = Referee.objects.filter(pk=referee_id).order_by()

    referees = (referees
                .prefetch_related(
                    Prefetch('actions',
                             queryset=ReferenceAction.objects.select_related('user')))
                .select_related('reference',
                                'application',
                                'application__officer'))

    all_referees = list(referees)
    if 'ref_email' in request.GET:
        ref_email = request.GET['ref_email']
        c['ref_email_search'] = ref_email
        all_referees = [r for r in all_referees if r.email.lower() == ref_email.lower()]
    else:
        ref_email = None

    received = [r for r in all_referees if r.reference_is_received()]
    requested = [r for r in all_referees if not r.reference_is_received() and r.reference_was_requested()]
    notrequested = [r for r in all_referees if not r.reference_is_received() and not r.reference_was_requested()]

    for referee in all_referees:
        if referee.reference_is_received():
            continue  # Don't need the following
        # decorate each Reference with suggested previous References.
        add_previous_references(referee)

    if referee_id is None:
        c['notrequested'] = notrequested
        c['requested'] = requested
        c['received'] = received
        template_name = 'cciw/officers/manage_references.html'
    else:
        if received:
            c['mode'] = 'received'
            c['referee'] = received[0]
        elif requested:
            c['mode'] = 'requested'
            c['referee'] = requested[0]
        else:
            c['mode'] = 'notrequested'
            c['referee'] = notrequested[0]
        template_name = 'cciw/officers/manage_reference.html'

    return render(request, template_name, c)


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
def officer_history(request, officer_id=None):
    officer = get_object_or_404(User.objects.filter(id=int(officer_id)))
    referee_pairs = [app.referees
                     for app in (officer.applications.all()
                                 .prefetch_related('referee_set',
                                                   'referee_set__reference')
                                 .order_by('-date_submitted'))
                     ]

    return render(request, "cciw/officers/officer_history.html",
                  {'officer': officer,
                   'referee_pairs': referee_pairs,
                   })


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
def request_reference(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    try:
        referee_id = int(request.GET.get('referee_id'))
    except (ValueError, TypeError):
        raise Http404
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    app = referee.application

    c = {}

    emailform = None

    # Need to handle any changes to the referees first, for correctness of what
    # follows
    if request.method == "POST" and 'setemail' in request.POST:
        emailform = SetEmailForm(request.POST)
        if emailform.is_valid():
            emailform.save(referee)
            messages.info(request, "Name/email address updated.")

    # Work out 'old_referee' or 'known_email_address', and the URL to use in the
    # message.
    update = 'update' in request.GET
    if update:
        add_previous_references(referee)
        prev_ref_id = int(request.GET['prev_ref_id'])
        if referee.previous_reference is not None:
            if referee.previous_reference.id != prev_ref_id:
                # the prev_ref_id must be the same as exact.id by the logic of
                # the buttons available on the manage_references page. If not
                # true, we close the page and update the parent page, in case
                # the parent is out of date.
                return close_window_and_update_referee(referee_id)
            c['known_email_address'] = True
            prev_reference = referee.previous_reference
        else:
            # Get old referee data
            prev_references = [r for r in referee.possible_previous_references if r.id == prev_ref_id]
            assert len(prev_references) == 1
            prev_reference = prev_references[0]
            c['old_referee'] = prev_reference.referee
        url = make_ref_form_url(referee.id, prev_ref_id)
    else:
        url = make_ref_form_url(referee.id, None)
        prev_reference = None

    messageform_info = dict(referee=referee,
                            applicant=app.officer,
                            camp=camp,
                            url=url,
                            sender=request.user,
                            update=update)
    messageform = None

    editreferenceform = None

    if request.method == 'POST':
        if 'send' in request.POST:
            c['show_messageform'] = True
            messageform = SendReferenceRequestForm(request.POST, message_info=messageform_info)
            if messageform.is_valid():
                send_reference_request_email(wordwrap(messageform.cleaned_data['message'], 70), referee, request.user, camp)
                referee.log_request_made(request.user, timezone.now())
                return close_window_and_update_referee(referee_id)
        elif 'save' in request.POST:
            c['show_editreferenceform'] = True
            reference = referee.reference if hasattr(referee, 'reference') else None
            editreferenceform = AdminReferenceForm(request.POST, instance=reference)
            if editreferenceform.is_valid():
                editreferenceform.save(referee, user=request.user)
                return close_window_and_update_referee(referee_id)
        elif 'cancel' in request.POST:
            return close_window_response()

    if emailform is None:
        emailform = SetEmailForm(initial={'email': referee.email,
                                          'name': referee.name,
                                          })
    if messageform is None:
        messageform = SendReferenceRequestForm(message_info=messageform_info)

    if editreferenceform is None:
        reference = referee.reference if hasattr(referee, 'reference') else None
        editreferenceform = get_initial_reference_form(reference,
                                                       referee, prev_reference,
                                                       AdminReferenceForm)

    if not is_valid_email(referee.email.strip()):
        c['bad_email'] = True
    c['is_popup'] = True
    c['already_requested'] = referee.reference_was_requested()
    c['referee'] = referee
    c['app'] = app
    c['is_update'] = update
    c['emailform'] = emailform
    c['messageform'] = messageform
    c['editreferenceform'] = editreferenceform

    return render(request, 'cciw/officers/request_reference.html', c)


@staff_member_required
@camp_admin_required  # we don't care which camp they are admin for.
def nag_by_officer(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    try:
        referee_id = int(request.GET.get('referee_id'))
    except (ValueError, TypeError):
        raise Http404
    referee = get_object_or_404(Referee.objects.filter(id=referee_id))
    app = referee.application
    officer = app.officer

    c = {}
    messageform_info = dict(referee=referee,
                            officer=officer,
                            sender=request.user,
                            camp=camp)

    if request.method == 'POST':
        if 'send' in request.POST:
            messageform = SendNagByOfficerForm(request.POST, message_info=messageform_info)
            # It's impossible for the form to be invalid, so assume valid
            messageform.is_valid()
            send_nag_by_officer(wordwrap(messageform.cleaned_data['message'], 70),
                                officer, referee, request.user)
            referee.log_nag_made(request.user, timezone.now())
            return close_window_and_update_referee(referee_id)
        else:
            # cancel
            return close_window_response()

    messageform = SendNagByOfficerForm(message_info=messageform_info)

    c['referee'] = referee
    c['app'] = app
    c['officer'] = officer
    c['messageform'] = messageform
    c['is_popup'] = True
    return render(request, 'cciw/officers/nag_by_officer.html', c)


def initial_reference_form_data(referee, prev_reference):
    """
    Return the initial data to be used for Reference, given the current
    Referee object and the Reference object with data to be copied.
    """
    retval = {}
    if prev_reference is not None:
        # Copy data over
        for f in Reference._meta.fields:
            fname = f.attname
            if fname not in ['id', 'date_created']:
                retval[fname] = getattr(prev_reference, fname)
    retval['referee_name'] = referee.name
    return retval


def create_reference_form(request, referee_id="", prev_ref_id="", hash=""):
    """
    View for allowing referee to submit reference (create the Reference object)
    """
    c = {}
    if hash != make_ref_form_url_hash(referee_id, prev_ref_id):
        c['incorrect_url'] = True
    else:
        referee = get_object_or_404(Referee.objects.filter(id=int(referee_id)))
        prev_reference = None
        if prev_ref_id != "":
            prev_reference = get_object_or_404(Reference.objects.filter(id=int(prev_ref_id)))

        if prev_reference is not None:
            c['update'] = True
            c['last_form_date'] = prev_reference.date_created if not prev_reference.inaccurate else None
            c['last_empty'] = empty_reference(prev_reference)

        reference = referee.reference if hasattr(referee, 'reference') else None

        if reference is not None and not empty_reference(reference):
            # It's possible that empty references have been created in the past,
            # so ensure that these don't stop people filling out form.
            c['already_submitted'] = True
        else:
            if request.method == 'POST':
                form = ReferenceForm(request.POST, instance=reference)
                if form.is_valid():
                    form.save(referee)
                    return HttpResponseRedirect(reverse('cciw-officers-create_reference_thanks'))
            else:
                form = get_initial_reference_form(reference, referee, prev_reference, ReferenceForm)
            c['form'] = form
        c['officer'] = referee.application.officer
    return render(request, 'cciw/officers/create_reference.html', c)


def get_initial_reference_form(reference, referee, prev_reference, form_class):
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


def create_reference_thanks(request):
    return render(request, 'cciw/officers/create_reference_thanks.html', {})


@staff_member_required
@camp_admin_required
def view_reference(request, reference_id=None):
    reference = get_object_or_404(Reference.objects.filter(id=reference_id))
    c = {}
    c['reference'] = reference
    c['officer'] = reference.referee.application.officer
    c['referee'] = reference.referee
    c['is_popup'] = True

    return render(request, "cciw/officers/view_reference_form.html", c)


@staff_member_required
@camp_admin_required
def officer_list(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)

    c = {}
    c['camp'] = camp
    invitation_list = camp.invitations.all()
    officer_list_ids = set(i.officer_id for i in invitation_list)
    c['invitations'] = invitation_list
    c['officers_noapplicationform'] = camp_slacker_list(camp)
    c['address_all'] = address_for_camp_officers(camp)
    c['address_noapplicationform'] = address_for_camp_slackers(camp)
    c['officers_serious_slackers'] = camp_serious_slacker_list(camp)

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
            retval[section] = render_to_string(tname, c, request=request)
        return HttpResponse(python_to_json(retval),
                            content_type="text/javascript")
    else:
        return render(request, "cciw/officers/officer_list.html", c)


@staff_member_required
@camp_admin_required
@json_response
def remove_officer(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    officer_id = request.POST['officer_id']
    Invitation.objects.filter(camp=camp.id, officer=int(officer_id)).delete()
    return {'status': 'success'}


@staff_member_required
@camp_admin_required
@json_response
def add_officers(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    for officer_id in request.POST['officer_ids'].split(','):
        try:
            Invitation.objects.get(camp=camp, officer=User.objects.get(id=int(officer_id)))
        except Invitation.DoesNotExist:
            Invitation.objects.create(camp=camp,
                                      officer=User.objects.get(id=int(officer_id)),
                                      date_added=date.today())
    return {'status': 'success'}


@staff_member_required
@camp_admin_required
@json_response
def update_officer(request):
    form = UpdateOfficerForm(request.POST)
    if form.is_valid():
        officer_id = int(request.POST['officer_id'])
        camp_id = int(request.POST['camp_id'])
        form.save(officer_id, camp_id)
        return {'status': 'success'}
    else:
        raise ValidationError(form.errors)


def correct_email(request):
    c = {}
    try:
        username, new_email = signing.loads(request.GET.get('t', ''),
                                            salt="cciw-officers-correct_email",
                                            max_age=60 * 60 * 24 * 10)  # 10 days
    except signing.BadSignature:
        c['message'] = ("The URL was invalid. Please ensure you copied the URL from the email correctly, "
                        "or contact the webmaster if you are having difficulties")
    else:
        u = get_object_or_404(User.objects.filter(username=username))
        u.email = new_email
        u.save()
        c['message'] = "Your email address has been updated, thanks."
        c['success'] = True

    return render(request, 'cciw/officers/email_update.html', c)


def correct_application(request):
    c = {}
    try:
        application_id, email = signing.loads(request.GET.get('t', ''),
                                              salt="cciw-officers-correct_application",
                                              max_age=60 * 60 * 24 * 10)  # 10 days
    except signing.BadSignature:
        c['message'] = ("The URL was invalid. Please ensure you copied the URL from the email correctly, "
                        "or contact the webmaster if you are having difficulties.")
    else:
        application = get_object_or_404(Application.objects.filter(id=application_id))
        application.address_email = email
        application.save()
        c['message'] = "Your application form email address has been updated, thanks."
        c['success'] = True

    return render(request, 'cciw/officers/email_update.html', c)


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
                    duplicate_message = "A user with that name and email address already exists. You can change the details above and try again."
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
                        duplicate_message = "A user with that email address already exists:"
                    else:
                        duplicate_message = "%d users with that email address already exist:"\
                                            % len(existing_users)
                else:
                    process_form = True

            elif "confirm" in request.POST:
                process_form = True

            if process_form:
                u = form.save()
                form = CreateOfficerForm()
                messages.info(request, "Officer %s has been added and emailed.  You can add another if required, or close this popup to continue." % u.username)
                camp_id = request.GET.get('camp_id')
                if camp_id is not None:
                    Invitation.objects.get_or_create(camp=Camp.objects.get(id=camp_id), officer=u)

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
    create.email_officer(u.username, u.first_name, u.email, password, update=True)
    return {'status': 'success'}


@staff_member_required
@camp_admin_required
def export_officer_data(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(officer_data_to_spreadsheet(camp, formatter),
                                "camp-%s-officers" % camp.slug_name_with_year)


@staff_member_required
@camp_admin_required
def export_camper_data(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(camp_bookings_to_spreadsheet(camp, formatter),
                                "camp-%s-campers" % camp.slug_name_with_year)


@staff_member_required
@booking_secretary_required
def export_camper_data_for_year(request, year=None):
    year = int(year)
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(year_bookings_to_spreadsheet(year, formatter),
                                "CCIW-bookings-%d" % year)


@staff_member_required
@camp_admin_required
def export_sharable_transport_details(request, year=None, slug=None):
    camp = _get_camp_or_404(year, slug)
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(camp_sharable_transport_details_to_spreadsheet(camp, formatter),
                                "camp-%s-transport-details" % camp.slug_name_with_year)


officer_files = access_folder_securely("officers",
                                       lambda request: request.user.is_authenticated() and is_camp_officer(request.user))


@staff_member_required
@camp_admin_required
def officer_stats(request, year=None):
    year = int(year)
    camps = list(Camp.objects.filter(year=year).order_by('camp_name__slug'))
    if len(camps) == 0:
        raise Http404

    ctx = {
        'camps': camps,
        'year': year,
    }
    charts = []
    for camp in camps:
        df = get_camp_officer_stats(camp)
        df['References ÷ 2'] = df['References'] / 2  # Make it match the height of others
        df.pop('References')
        charts.append((camp,
                       pandas_highcharts.core.serialize(df,
                                                        title="{0} - {1}".format(camp.name, camp.leaders_formatted),
                                                        output_type='json')))
    ctx['charts'] = charts
    return render(request, 'cciw/officers/stats.html', ctx)


@staff_member_required
@camp_admin_required
def officer_stats_trend(request, start_year=None, end_year=None):
    start_year = int(start_year)
    end_year = int(end_year)
    data = get_camp_officer_stats_trend(start_year, end_year)
    for c in data.columns:
        if 'fraction' not in c:
            data.pop(c)

    fraction_to_percent(data)

    ctx = {
        'start_year': start_year,
        'end_year': end_year,
        'chart_data': pandas_highcharts.core.serialize(data,
                                                       title="Officer stats {0} - {1}".format(start_year, end_year),
                                                       output_type='json')
    }
    return render(request, 'cciw/officers/stats_trend.html', ctx)


def fraction_to_percent(data):
    for col_name in list(data.columns):
        parts = col_name.split(" ")
        new_name = " ".join("%" if p.lower() == "fraction" else p for p in parts)
        if new_name != col_name:
            data[new_name] = data[col_name] * 100
            data.pop(col_name)


@staff_member_required
@camp_admin_required
def officer_stats_download(request, year):
    year = int(year)
    camps = list(Camp.objects.filter(year=year).order_by('camp_name__slug'))
    formatter = get_spreadsheet_formatter(request)
    for camp in camps:
        formatter.add_sheet_from_dataframe(camp.slug_name_with_year,
                                           get_camp_officer_stats(camp))
    return spreadsheet_response(formatter,
                                "officer-stats-%d" % year)


@staff_member_required
@camp_admin_required
def officer_stats_trend_download(request, start_year, end_year):
    start_year = int(start_year)
    end_year = int(end_year)
    formatter = get_spreadsheet_formatter(request)
    formatter.add_sheet_from_dataframe("Officer stats trend",
                                       get_camp_officer_stats_trend(start_year, end_year))
    return spreadsheet_response(formatter,
                                "officer-stats-trend-{0}-{1}".format(start_year, end_year))


@staff_member_required
@camp_admin_required
def manage_crbs(request, year=None):
    year = int(year)
    now = timezone.now()
    # We need a lot of information. Try to get it in a few up-front queries
    camps = list(Camp.objects.filter(year=year).order_by('camp_name__slug'))
    if len(camps) == 0:
        raise Http404
    # Selected camps:
    # We need to support URLs that indicate which camp to select, so we
    # can permalink nicely.
    selected_camp_slugs = None
    if 'camp' in request.GET:
        try:
            selected_camp_slugs = set(request.GET.getlist('camp'))
        except ValueError:
            pass
    if not selected_camp_slugs:  # empty or None
        # Assume all, because having none is never useful
        selected_camp_slugs = set([c.slug_name for c in camps])

    # We need all the officers, and we need to know which camp(s) they belong
    # to. Even if we have only selected one camp, it might be nice to know if
    # they are on other camps. So we get data for all camps, and filter later.
    # We also want to be able to filtering by javascript in the frontend.
    camps_officers = [[i.officer for i in c.invitations.all()] for c in camps]
    all_officers = reduce(operator.or_, map(set, camps_officers))
    all_officers = sorted(all_officers, key=lambda o: (o.first_name, o.last_name))
    apps = list(reduce(operator.or_, map(applications_for_camp, camps)))
    valid_crb_officer_ids = set(reduce(operator.or_,
                                       [CRBApplication.objects.get_for_camp(c, include_late=True)
                                        for c in camps])
                                .values_list('officer_id', flat=True))
    all_crb_officer_ids = set(CRBApplication.objects.values_list('officer_id', flat=True))
    # CRB forms sent: set cutoff to a year before now, on the basis that
    # anything more than that will have been lost, and we don't want to load
    # everything into membery.
    crb_forms_sent = list(CRBFormLog.objects.filter(sent__gt=now - timedelta(365)).order_by('sent'))
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
                if c.slug_name in selected_camp_slugs:
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
         'selected_camps': selected_camp_slugs,
         'year': year}
    return render(request, 'cciw/officers/manage_crbs.html', c)


@staff_member_required
@camp_admin_required
@json_response
def mark_crb_sent(request):
    officer_id = int(request.POST['officer_id'])
    officer = User.objects.get(id=officer_id)
    c = CRBFormLog.objects.create(officer=officer,
                                  sent=timezone.now())
    return {'status': 'success',
            'crbFormLogId': str(c.id)
            }


@staff_member_required
@camp_admin_required
@json_response
def undo_mark_crb_sent(request):
    crbformlog_id = int(request.POST['crbformlog_id'])
    CRBFormLog.objects.filter(id=crbformlog_id).delete()
    return {'status': 'success'}


@staff_member_required
@camp_admin_required
def crb_consent_problem(request):
    try:
        app_id = int(request.GET.get('application_id'))
    except (ValueError, TypeError):
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


@staff_member_required
def officer_info(request):
    return render(request, 'cciw/officers/info.html', {
        'show_wiki_link': is_wiki_user(request.user),
    })


@booking_secretary_required
def booking_secretary_reports(request, year=None):
    from cciw.bookings.models import SEX_MALE, SEX_FEMALE, Booking, \
        Price
    year = int(year)

    # 1. Camps and their booking levels.

    camps = Camp.objects.filter(year=year).prefetch_related('bookings')
    # Do some filtering in Python to avoid multiple db hits
    for c in camps:
        c.booked_places = [b for b in c.bookings.booked()]
        c.confirmed_bookings = [b for b in c.booked_places if b.is_confirmed]
        c.confirmed_bookings_boys = [b for b in c.confirmed_bookings if b.sex == SEX_MALE]
        c.confirmed_bookings_girls = [b for b in c.confirmed_bookings if b.sex == SEX_FEMALE]

    # 2. Online bookings needing attention
    to_approve = Booking.objects.need_approving().filter(camp__year__exact=year)

    # 3. Fees

    bookings = Booking.objects.filter(camp__year__exact=year)
    # We need to include 'full refund' cancelled bookings in case they overpaid,
    # as well as all 'payable' bookings.
    bookings = bookings.payable(True, False) | bookings.cancelled()

    # 3 concerns:
    # 1) people who have overpaid. This must be calculated with respect to the total amount due
    #    on the account.
    # 2) people who have underpaid:
    #    a) with respect to the total amount due
    #    b) with respect to the total amount due at this point in time,
    #       allowing for the fact that up to a certain point,
    #       only the deposit is actually required.
    #
    # People in group 2b) possibly need to be chased. They are not highlighted here - TODO

    bookings = bookings.order_by('account__name', 'first_name', 'last_name')
    bookings = list(bookings.prefetch_related('camp',
                                              'account',
                                              'account__bookings',
                                              'account__bookings__camp',
                                              ))

    counts = defaultdict(int)
    for b in bookings:
        counts[b.account_id] += 1

    deposit_prices = Price.get_deposit_prices()
    outstanding = []
    for b in bookings:
        b.count_for_account = counts[b.account_id]
        if not hasattr(b.account, 'calculated_balance'):
            b.account.calculated_balance = b.account.get_balance(confirmed_only=True,
                                                                 allow_deposits=False)
            b.account.calculated_balance_due = b.account.get_balance(confirmed_only=True,
                                                                     allow_deposits=True,
                                                                     deposit_price_dict=deposit_prices)

            if b.account.calculated_balance_due > 0 or b.account.calculated_balance < 0:
                outstanding.append(b)

    export_start = datetime(year - 1, 11, 1)  # November previous year
    export_end = datetime(year, 10, 31)  # November this year
    export_data_link = (reverse('cciw-officers-export_payment_data') +
                        "?start=%s&end=%s" % (export_start.strftime(EXPORT_PAYMENT_DATE_FORMAT),
                                              export_end.strftime(EXPORT_PAYMENT_DATE_FORMAT)
                                              )
                        )

    return render(request, 'cciw/officers/booking_secretary_reports.html',
                  {'year': year,
                   'stats_start_year': year - 4,
                   'camps': camps,
                   'bookings': outstanding,
                   'to_approve': to_approve,
                   'export_start': export_start,
                   'export_end': export_end,
                   'export_data_link': export_data_link,
                   })


@booking_secretary_required
def export_payment_data(request):
    date_start = request.GET['start']
    date_end = request.GET['end']
    date_start = timezone.get_default_timezone().localize(datetime.strptime(date_start, EXPORT_PAYMENT_DATE_FORMAT))
    date_end = timezone.get_default_timezone().localize(datetime.strptime(date_end, EXPORT_PAYMENT_DATE_FORMAT))
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(payments_to_spreadsheet(date_start, date_end, formatter),
                                "payments-%s-to-%s" % (date_start.strftime('%Y-%m-%d'),
                                                       date_end.strftime('%Y-%m-%d')))


def _parse_year_or_camp_params(start_year, end_year, camps):
    if camps is not None:
        camp_ids = camps.split(',')
        try:
            camp_objs = [Camp.objects.get(year=int(camp.split('-')[0]),
                                          camp_name__slug=camp.split('-')[1])
                         for camp in camp_ids]
        except Camp.DoesNotExist:
            raise Http404()
        return None, None, camp_objs
    else:
        return int(start_year), int(end_year), None


def _get_booking_progress_stats_from_params(start_year, end_year, camps, **kwargs):
    start_year, end_year, camps = _parse_year_or_camp_params(start_year, end_year, camps)
    if camps is not None:
        data_dates, data_rel_days = get_booking_progress_stats(camps=camps, **kwargs)
    else:
        data_dates, data_rel_days = get_booking_progress_stats(start_year=start_year,
                                                               end_year=end_year, **kwargs)

    return start_year, end_year, camps, data_dates, data_rel_days


@staff_member_required
@camp_admin_required
def booking_progress_stats(request, start_year=None, end_year=None, camps=None):
    start_year, end_year, camp_objs, data_dates, data_rel_days = (
        _get_booking_progress_stats_from_params(start_year, end_year, camps, overlay_years=True)
    )

    ctx = {
        'start_year': start_year,
        'end_year': end_year,
        'camps': camp_objs,
        'camps_param': camps,
        'dates_chart_data': pandas_highcharts.core.serialize(data_dates,
                                                             title="Bookings by date",
                                                             output_type='json'),
        'rel_days_chart_data': pandas_highcharts.core.serialize(data_rel_days,
                                                                title="Bookings by days relative to start of camp",
                                                                output_type='json'),
    }
    return render(request, 'cciw/officers/booking_progress_stats.html', ctx)


@staff_member_required
@camp_admin_required
def booking_progress_stats_download(request, start_year=None, end_year=None, camps=None):
    start_year, end_year, camp_objs, data_dates, data_rel_days = (
        _get_booking_progress_stats_from_params(start_year, end_year, camps, overlay_years=False)
    )
    formatter = get_spreadsheet_formatter(request)
    formatter.add_sheet_from_dataframe("Bookings against date", data_dates)
    formatter.add_sheet_from_dataframe("Days relative to start of camp", data_rel_days)
    if camps is not None:
        filename = "booking-progress-stats-{0}".format(camps.replace(",", "_"))
    else:
        filename = "booking-progress-stats-{0}-{1}".format(start_year, end_year)
    return spreadsheet_response(formatter, filename)


@staff_member_required
@secretary_or_committee_required
def booking_summary_stats(request, start_year, end_year):
    start_year = int(start_year)
    end_year = int(end_year)
    chart_data = get_booking_summary_stats(start_year, end_year)
    chart_data.pop('Total')
    ctx = {
        'start_year': start_year,
        'end_year': end_year,
        'chart_data': pandas_highcharts.core.serialize(chart_data, output_type='json')
    }
    return render(request, 'cciw/officers/booking_summary_stats.html', ctx)


@staff_member_required
@secretary_or_committee_required
def booking_summary_stats_download(request, start_year, end_year):
    start_year = int(start_year)
    end_year = int(end_year)
    data = get_booking_summary_stats(start_year, end_year)
    formatter = get_spreadsheet_formatter(request)
    formatter.add_sheet_from_dataframe("Bookings", data)
    return spreadsheet_response(formatter,
                                "booking-summary-stats-{0}-{1}".format(start_year, end_year))


def _get_booking_ages_stats_from_params(start_year, end_year, camps):
    start_year, end_year, camps = _parse_year_or_camp_params(start_year, end_year, camps)
    if camps is not None:
        data = get_booking_ages_stats(camps=camps, include_total=True)
    else:
        data = get_booking_ages_stats(start_year=start_year,
                                      end_year=end_year, include_total=False)
    return start_year, end_year, camps, data


@staff_member_required
@camp_admin_required
def booking_ages_stats(request, start_year=None, end_year=None, camps=None, single_year=None):
    if single_year is not None:
        camps = Camp.objects.filter(year=int(single_year))
        return HttpResponseRedirect(reverse('cciw-officers-booking_ages_stats_custom',
                                            kwargs={'camps':
                                                    ','.join(c.slug_name_with_year for c in camps)}))
    start_year, end_year, camp_objs, data = (
        _get_booking_ages_stats_from_params(start_year, end_year, camps)
    )
    if 'Total' in data:
        data.pop('Total')

    if camp_objs:
        if all(c.year == camp_objs[0].year for c in camp_objs):
            stack_columns = True
        else:
            stack_columns = False
    else:
        stack_columns = False

    # Use colors defined for camps if possible. To get them to line up with data
    # series, we have to sort in the same way the pandas_highcharts does i.e. by
    # series name
    colors = []
    if camp_objs:
        colors = [color for (title, color) in
                  sorted([(c.slug_name_with_year, c.camp_name.color)
                          for c in camp_objs])]
        if len(set(colors)) != len(colors):
            # Not enough - fall back to auto
            colors = []

    ctx = {
        'start_year': start_year,
        'end_year': end_year,
        'camps': camp_objs,
        'camps_param': camps,
        'chart_data': pandas_highcharts.core.serialize(data,
                                                       title="Age of campers",
                                                       output_type='json'),
        'colors_data': colors,
        'stack_columns': stack_columns,
    }
    return render(request, 'cciw/officers/booking_ages_stats.html', ctx)


@staff_member_required
@camp_admin_required
def booking_ages_stats_download(request, start_year=None, end_year=None, camps=None):
    start_year, end_year, camp_objs, data = (
        _get_booking_ages_stats_from_params(start_year, end_year, camps)
    )
    formatter = get_spreadsheet_formatter(request)
    formatter.add_sheet_from_dataframe("Age of campers", data)
    if camps is not None:
        filename = "booking-ages-stats-{0}".format(camps.replace(",", "_"))
    else:
        filename = "booking-ages-stats-{0}-{1}".format(start_year, end_year)
    return spreadsheet_response(formatter, filename)


@cciw_secretary_or_booking_secretary_required
def brochure_mailing_list(request, year):
    formatter = get_spreadsheet_formatter(request)
    return spreadsheet_response(addresses_for_mailing_list(int(year), formatter),
                                "mailing-list-%s" % year)


def spreadsheet_response(formatter, filename):
    response = HttpResponse(formatter.to_bytes(),
                            content_type=formatter.mimetype)
    response['Content-Disposition'] = "attachment; filename={0}.{1}".format(filename, formatter.file_ext)
    return response


class UserAutocomplete(autocomplete.Select2QuerySetView):

    def get_result_label(self, user):
        return "%s %s <%s>" % (user.first_name, user.last_name, user.email)

    def get_queryset(self):
        request = self.request
        if request.user.is_authenticated() and is_camp_admin(request.user):
            qs = User.objects.all().order_by('first_name', 'last_name', 'email')
            return (qs.filter(first_name__istartswith=self.q) |
                    qs.filter(last_name__istartswith=self.q))
        else:
            return User.objects.none()
