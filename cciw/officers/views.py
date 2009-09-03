import itertools
import re
import datetime
from django import forms
from django import template
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from cciw.cciwmain import common
from cciw.cciwmain.models import Person, Camp
from cciw.cciwmain.utils import all, StandardReprMixin
from cciw.cciwmain.views.memberadmin import email_hash
from cciw.mail.lists import address_for_camp_officers, address_for_camp_slackers
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_txt_filename
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email, make_update_email_hash
from cciw.officers.models import Application, Reference, ReferenceForm
from cciw.officers.utils import camp_officer_list, camp_slacker_list

def _copy_application(application):
    new_obj = Application(id=None)
    for field in Application._meta.fields:
        if field.attname != 'id':
            setattr(new_obj, field.attname, getattr(application, field.attname))
    new_obj.camp = None
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

def _is_camp_admin(user):
    return (user.groups.filter(name='Leaders').count() > 0) \
        or user.camps_as_admin.count() > 0

def _camps_as_admin_or_leader(user):
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

    return camps

# /officers/
@staff_member_required
@never_cache
def index(request):
    """Displays a list of links/buttons for various actions."""
    user = request.user
    context = template.RequestContext(request)
    if _is_camp_admin(user):
        context['show_leader_links'] = True
        context['show_admin_link'] = True

    return render_to_response('cciw/officers/index.html', context_instance=context)

@staff_member_required
@user_passes_test(_is_camp_admin)
def leaders_index(request):
    """Displays a list of links for actions for leaders"""
    user = request.user
    context = template.RequestContext(request)
    thisyear = common.get_thisyear()
    context['current_camps'] = _camps_as_admin_or_leader(user).filter(year=thisyear)
    context['old_camps'] = _camps_as_admin_or_leader(user).filter(year__lt=thisyear)

    return render_to_response('cciw/officers/leaders_index.html', context_instance=context)

@staff_member_required
@never_cache
def applications(request):
    """Displays a list of tasks related to applications."""
    user = request.user
    context = template.RequestContext(request)
    context['finished_applications'] = user.application_set.filter(finished=True).order_by('-date_submitted')
    context['unfinished_applications'] = user.application_set.filter(finished=False).order_by('-date_submitted')

    if request.POST.has_key('edit'):
        # Edit existing application
        id = request.POST.get('edit_application', None)
        if id is not None:
            return HttpResponseRedirect('/admin/officers/application/%s/' % id)
    elif request.POST.has_key('new'):
        # Create new application based on old one
        obj = None
        try:
            id = int(request.POST['new_application'])
        except (ValueError, KeyError):
            id = None
        if id is not None:
            try:
                obj = Application.objects.get(pk=id)
            except Application.DoesNotExist:
                # should never get here
                obj = None
        if obj is not None:
            # Create a copy
            new_obj = _copy_application(obj)
            # We *have* to set 'camp' otherwise object cannot be seen
            # in admin, due to default 'ordering'
            next_camps = list(obj.camp.next_camps.all())
            if len(next_camps) > 0:
                new_obj.camp = next_camps[0]
            else:
                new_obj.camp = Camp.objects.filter(online_applications=True).order_by('-year', 'number')[0]
            new_obj.save()
            return HttpResponseRedirect('/admin/officers/application/%s/' % new_obj.id)

    elif request.POST.has_key('delete'):
        # Delete an unfinished application
        pass

    return render_to_response('cciw/officers/applications.html', context_instance=context)

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
        resp['Content-Disposition'] = 'attachment; filename=%s;' % application_txt_filename(app)
        return resp
    elif format == 'rtf':
        resp = HttpResponse(application_to_rtf(app), mimetype="text/rtf")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % application_rtf_filename(app)
        return resp
    elif format == 'send':
        application_text = application_to_text(app)
        application_rtf = application_to_rtf(app)
        rtf_attachment = (application_rtf_filename(app), application_rtf, 'text/rtf')

        msg = \
u"""Dear %s,

Please find attached a copy of the application you requested
 -- in plain text below and an RTF version attached.

""" % request.user.first_name
        msg = msg + application_text

        send_mail_with_attachments("Copy of CCIW application - %s" % app.full_name , msg, settings.SERVER_EMAIL,
                                   [formatted_email(request.user)] , attachments=[rtf_attachment])
        request.user.message_set.create(message="Email sent.")

        # Redirect back where we came from
        return HttpResponseRedirect(request.POST.get('to', '/officers/'))

    else:
        raise Http404

    return resp


def _thisyears_camp_for_leader(user):
    leaders = list(user.person_set.all())
    try:
        return leaders[0].camps_as_leader.get(year=common.get_thisyear(), online_applications=True)
    except (ObjectDoesNotExist, IndexError):
        return None

@staff_member_required
@user_passes_test(_is_camp_admin)
@never_cache
def manage_applications(request, year=None, number=None):
    user = request.user
    camp = _get_camp_or_404(year, number)
    context = template.RequestContext(request)
    context['finished_applications'] =  camp.application_set.filter(finished=True)
    context['camp'] = camp

    return render_to_response('cciw/officers/manage_applications.html', context_instance=context)

def _get_camp_or_404(year, number):
    try:
        return Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist, ValueError:
        raise Http404


@staff_member_required
@user_passes_test(_is_camp_admin) # we don't care which camp they are admin for.
def manage_references(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp

    apps = camp.application_set.filter(finished=True)
    # force creation of Reference objects.
    [a.references for a in apps]

    # TODO - check for case where user has submitted multiple application forms.
    # User.objects.all().filter(application__camp=camp).annotate(num_applications=models.Count('application')).filter(num_applications__gt=1)

    refinfo = Reference.objects.filter(application__camp=camp, application__finished=True).order_by('application__officer__first_name', 'referee_number')
    received = refinfo.filter(received=True)
    requested = refinfo.filter(received=False, requested=True)
    notrequested = refinfo.filter(received=False, requested=False)

    for l in (received, requested, notrequested):
        # decorate each Reference with suggested previous ReferenceForms.
        for curref in l:
            # Look for ReferenceForms for same officer, within the previous five
            # years.  Don't look for references from this year's
            # application (which will be the other referee).
            cutoffdate = curref.application.camp.start_date - datetime.timedelta(365*5)
            prev = list(ReferenceForm.objects.filter(reference_info__application__officer=curref.application.officer,
                                                     reference_info__application__finished=True,
                                                     date_created__gte=cutoffdate).exclude(reference_info__application=curref.application).order_by('-reference_info__application__camp__year'))

            # Sort by relevance
            def relevance_key(refform):
                # Matching name or e-mail address is better, so has lower value,
                # so it comes first.
                return -(int(refform.reference_info.referee.email==curref.referee.email) +
                         int(refform.reference_info.referee.name ==curref.referee.name))
            prev.sort(key=relevance_key)

            exact = None
            for refform in prev:
                if refform.reference_info.referee == curref.referee:
                    exact = refform.reference_info
            if exact is not None:
                curref.previous_reference = exact
            else:
                curref.possible_previous_references = [rf.reference_info for rf in prev]

    c['notrequested'] = notrequested
    c['requested'] = requested
    c['received'] = received

    return render_to_response('cciw/officers/manage_references.html',
                              context_instance=c)

class OfficerChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, u):
        return u"%s %s <%s>" % (u.first_name, u.last_name, u.email)

class OfficerListForm(forms.Form):
    officers = OfficerChoice(
        widget=forms.SelectMultiple(attrs={'class':'vSelectMultipleField'}),
        queryset=User.objects.filter(is_staff=True).order_by('first_name', 'last_name'),
        required=False
        )

@staff_member_required
@user_passes_test(_is_camp_admin)
def officer_list(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp

    if request.method == 'POST':
        print request.POST
        form = OfficerListForm(request.POST)
        if form.is_valid():
            camp.invitation_set.all().delete()
            print camp.invitation_set
            for o in form.cleaned_data['officers']:
                camp.invitation_set.create(officer=o).save()
    else:
        form = OfficerListForm({'officers': [unicode(inv.officer_id) for inv in camp.invitation_set.all()]})

    c['form'] = form

    # Make sure these queries come after the above data modification
    c['officers_all'] = camp_officer_list(camp)
    c['officers_noapplicationform'] = camp_slacker_list(camp)
    c['addresses_all'] = address_for_camp_officers(camp)
    c['addresses_noapplicationform'] = address_for_camp_slackers(camp)

    return render_to_response('cciw/officers/officer_list.html',
                              context_instance=c)

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

    return render_to_response('cciw/officers/email_update.html', context_instance=template.RequestContext(request, c))
