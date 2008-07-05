import re
import time
from django import newforms as forms
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
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_txt_filename
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from cciw.officers.models import Application, Reference

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
    context['finished_applications'] = user.application_set.filter(finished=True).order_by('-date_submitted')
    context['unfinished_applications'] = user.application_set.filter(finished=False).order_by('-date_submitted')
    if _is_camp_admin(user):
        context['show_leader_links'] = True
        context['camps_to_administer'] = _camps_as_admin_or_leader(user).filter(year=common.get_thisyear())  
    
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

    return render_to_response('cciw/officers/index.html', context_instance=context)

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
def manage_applications(request, year=None, number=None):
    user = request.user
    camp = _get_camp_or_404(year, number)
    context = template.RequestContext(request)
    context['finished_applications'] =  camp.application_set.filter(finished=True)
    context['camp'] = camp
    
    return render_to_response('cciw/officers/manage_applications.html', context_instance=context)

# Password reset
# admin/password_reset/

# Similar to version in django.contrib.auth.forms, but this one provides
# much better security

class CciwUserEmailField(forms.EmailField):
    def clean(self, value):
        value = super(CciwUserEmailField, self).clean(value)
        if User.objects.filter(email__iexact=value).count() == 0:
            raise forms.ValidationError("That e-mail address doesn't have an associated user account. Are you sure you've been registered?")
        return value

class PasswordResetForm(forms.Form):
    "A form that lets a user request a password reset"
    email = CciwUserEmailField(widget=forms.TextInput(attrs={'size':'40'}))

    def save(self, domain_override=None, email_template_name='cciw/officers/password_reset_email.txt'):
        "Generates a one-use only link for restting password and sends to the user"
        email = self.cleaned_data['email']
        for user in User.objects.filter(email__iexact=email):
            current_site = Site.objects.get_current()
            site_name = current_site.name
            t = template.loader.get_template(email_template_name)
            timestamp = int(time.time())
            c = {
                'email': user.email,
                'domain': current_site.domain,
                'site_name': site_name,
                'user': user,
                'hash': make_passwordreset_hash(user),
                }
            send_mail('Password reset on %s' % site_name, t.render(template.Context(c)), None, [user.email])

def make_passwordreset_hash(user):
    """
    Returns a hash that can be used once to do a password reset.
    """
    # By hashing on the internal state of the user and using state
    # that is sure to change (the password salt will change as soon as
    # the password is set, at least for current Django auth, and
    # last_login will also change), we produce a hash that will be
    # invalid as soon as it is used
    import md5
    return md5.new(settings.SECRET_KEY + unicode(user.id) + user.password + unicode(user.last_login)).hexdigest()

# This can be merged with 'PasswordChangeForm' using inheritance once
# it is complete and added to core
class SetPasswordForm(forms.Form):
    """
    A form that lets a user change set his/her password without
    entering the old password
    """
    new_password1 = forms.CharField(label=_("New password"), max_length=30, widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), max_length=30, widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save()
        return self.user

def password_reset_confirm(request, uid=None, hash=None, template_name='cciw/officers/password_reset_confirm.html'):
    """
    View that checks the hash and presents a form for entering a new password.
    """
    assert uid is not None and hash is not None # checked by URLconf
    user = get_object_or_404(User, id=uid)
    context_instance = template.RequestContext(request)

    if make_passwordreset_hash(user) == hash:
        context_instance['validlink'] = True
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect("../done/")
        else:
            form = SetPasswordForm(None)
    else:
        context_instance['validlink'] = False
        form = None
    context_instance['form'] = form    
    return render_to_response(template_name, context_instance=context_instance)

def _sort_apps(t1, t2):
    # Sorting function used below
    # Sort by 'received'
    rc = int(t1[3]) - int(t2[3])
    if rc != 0:
        return rc
    # Sort by 'requested'
    rq = int(t1[2]) - int(t2[2])
    # The list is already sorted by officer name, this should
    # be preserved in a stable sort
    return rq

def sort_app_details(tuplelist):
    tuplelist.sort(cmp=_sort_apps)
    return tuplelist

def get_app_details(camp):
    """Returns list of 4-tuples - 
    (this years app, 
    last years app (or None), 
    boolean indicating all references have been requested,
    boolean indicating all references have been received)
    """
    this_years_apps = list(camp.application_set.filter(finished=True).order_by('officer__first_name', 'officer__last_name'))
    last_years_apps = []
    requested = []
    received = []
    for app in this_years_apps:
        lastapp = list(app.officer.application_set.filter(camp__year__lt=camp.year).order_by('-camp__year'))
        if len(lastapp) == 0:
            lastapp = None
        else:
            # Pick the most recent
            lastapp = lastapp[0]
        last_years_apps.append(lastapp)
        requested.append(all(r is not None and r.requested for r in app.references)) 
        received.append(all(r is not None and r.received for r in app.references))
    return zip(this_years_apps, last_years_apps, requested, received)

def normalise_name(s):
    s = s.lower()
    for p in ["mr", "mr.", "pastor", "rev", "rev.", "mrs.", "mrs", "dr.", "dr", "prof", "prof."]:
        if s.startswith(p + " "):
            s = s[len(p)+1:]
            break
    s = re.sub("[ .]*(\(.*\))?[ .]*$", "", s) # remove trailing space or '.', and anything in brackets
    return s

def add_referee_counts(tuplelist):
    """Takes a tuple list [(thisyearsapp, prevyearsapp, requested, received)]
    and adds counts and pseudo ids for each referee on thisyearsapp."""
    refnames = [normalise_name(ref.name)
                for app in [t[0] for t in tuplelist]
                for ref in app.referees]
    counts = {}
    for name in refnames:
        counts[name] = counts.get(name, 0) + 1
    curid = 0
    for app, prevapp, requested, received in tuplelist: 
        for referee in app.referees:
            curid += 1
            referee.id = curid
            referee.usedcount = counts[normalise_name(referee.name)]
    return tuplelist

def _get_camp_or_404(year, number):
    try:
        return Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist, ValueError:
        raise Http404
   

@staff_member_required
@user_passes_test(_is_camp_admin)
def manage_references(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp

    # We have less validation than normal here, because
    # we basically trust the user, and the system is deliberately
    # fairly permissive (leaders can look at applications for
    # other camps, not just their own, etc).
    
    if request.method == 'POST':
        refs_updated = set()
        applist = map(int, request.POST.getlist('appids'))

        for appid in applist:
            for refnum in (1, 2):
                updated = False
                try:
                    ref = Reference.objects.get(application=appid, referee_number=refnum)
                except Reference.DoesNotExist:
                    # Create, but we only bother to save if it's 
                    # data is changed from empty.
                    ref = Reference(application_id=appid,
                                    referee_number=refnum,
                                    requested=False,
                                    received=False,
                                    comments="")
                req = ('req_%d_%d' % (refnum, appid)) in request.POST.keys()
                rec = ('rec_%d_%d' % (refnum, appid)) in request.POST.keys()
                comments = request.POST.get('comments_%d_%d' % (refnum, appid), "")
                
                if ref.requested != req or ref.received != rec or ref.comments != comments:
                    ref.requested, ref.received, ref.comments = req, rec, comments
                    ref.save()
                    refs_updated.add(ref)

        c['message'] = u"Information for %d references was updated." % len(refs_updated)

    c['application_forms'] = add_referee_counts(sort_app_details(get_app_details(camp)))

    return render_to_response('cciw/officers/manage_references.html',
                              context_instance=c)

class OfficerChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, u):
        return u"%s %s <%s>" % (u.first_name, u.last_name, u.email)

class OfficerListForm(forms.Form):
    officers = OfficerChoice(
        widget=forms.SelectMultiple(attrs={'class':'vSelectMultipleField'}),
        queryset=User.objects.filter(is_staff=True),
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
    c['officers_all'] = [i.officer for i in camp.invitation_set.all().select_related('officer')]
    finished_apps_off_ids = [o['officer__id'] 
                             for o in camp.application_set.filter(finished=True).values('officer__id')]
    c['officers_noapplicationform'] = [i.officer for i in camp.invitation_set.exclude(officer__in=finished_apps_off_ids).select_related('officer')]

    return render_to_response('cciw/officers/officer_list.html',
                              context_instance=c)
