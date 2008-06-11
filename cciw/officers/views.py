from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.views.main import add_stage, render_change_form
from django.contrib.admin.views.main import unquote, quote, get_text_list
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django import forms, template
from django.db import models
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.encoding import force_unicode, smart_str
import re

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType

from cciw.cciwmain.utils import all, StandardReprMixin

from cciw.officers.models import Application, Reference
from cciw.cciwmain.models import Person, Camp

from cciw.cciwmain import common
from django.views.decorators.cache import never_cache
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_txt_filename
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email

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


# /admin/officers/application/add/
@staff_member_required
def add_application(request):
    return add_stage(request, "officers", "application", show_delete=False, 
        form_url='', post_url="/officers/", post_url_continue='../%s/')


# /admin/officers/application/%s/

# Copied straight from django.contrib.admin.views.main,
# with small mods 
from django.utils.translation import gettext as _ 

@staff_member_required
@never_cache
def change_application(request, object_id):
    app_label, model_name = 'officers', 'application'
    model = models.get_model(app_label, model_name)
    object_id = unquote(object_id)
    if model is None:
        raise Http404, "App %r, model %r, not found" % (app_label, model_name)
    opts = model._meta

    # CHANGES
    user = request.user
    if not request.user.has_perm(app_label + '.' + opts.get_change_permission()):
        try:
            application = Application.objects.get(pk=object_id)
        except Application.DoesNotExist:
            raise Http404
        # only allow them to edit if they created it
        if application.officer_id != user.id:
            raise PermissionDenied

    if request.POST and request.POST.has_key("_saveasnew"):
        return add_application(request, app_label, model_name, form_url='../../add/')

    try:
        manipulator = model.ChangeManipulator(object_id)
    except ObjectDoesNotExist:
        raise Http404

    if request.method == 'POST':
        new_data = request.POST.copy()

        if opts.has_field_type(models.FileField):
            new_data.update(request.FILES)

        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)

        if not errors:
            new_object = manipulator.save(new_data)
            pk_value = new_object._get_pk_val()

            # Construct the change message.
            change_message = []
            if manipulator.fields_added:
                change_message.append(_('Added %s.') % get_text_list(manipulator.fields_added, _('and')))
            if manipulator.fields_changed:
                change_message.append(_('Changed %s.') % get_text_list(manipulator.fields_changed, _('and')))
            if manipulator.fields_deleted:
                change_message.append(_('Deleted %s.') % get_text_list(manipulator.fields_deleted, _('and')))
            change_message = ' '.join(change_message)
            if not change_message:
                change_message = _('No fields changed.')
            LogEntry.objects.log_action(request.user.id, ContentType.objects.get_for_model(model).id, pk_value, force_unicode(new_object), CHANGE, change_message)

            msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': opts.verbose_name, 'obj': new_object}
            if request.POST.has_key("_continue"):
                request.user.message_set.create(message=msg + ' ' + _("You may edit it again below."))
                if request.REQUEST.has_key('_popup'):
                    return HttpResponseRedirect(request.path + "?_popup=1")
                else:
                    return HttpResponseRedirect(request.path)
            elif request.POST.has_key("_saveasnew"):
                request.user.message_set.create(message=_('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': opts.verbose_name, 'obj': new_object})
                return HttpResponseRedirect("../%s/" % pk_value)
            elif request.POST.has_key("_addanother"):
                request.user.message_set.create(message=msg + ' ' + (_("You may add another %s below.") % opts.verbose_name))
                return HttpResponseRedirect("../add/")
            else:
                request.user.message_set.create(message=msg)
                return HttpResponseRedirect("/officers/")
    else:
        # Populate new_data with a "flattened" version of the current data.
        new_data = manipulator.flatten_data()

        # TODO: do this in flatten_data...
        # If the object has ordered objects on its admin page, get the existing
        # order and flatten it into a comma-separated list of IDs.

        id_order_list = []
        for rel_obj in opts.get_ordered_objects():
            id_order_list.extend(getattr(manipulator.original_object, 'get_%s_order' % rel_obj.object_name.lower())())
        if id_order_list:
            new_data['order_'] = ','.join(map(str, id_order_list))
        errors = {}

    # Populate the FormWrapper.
    form = forms.FormWrapper(manipulator, new_data, errors)
    form.original = manipulator.original_object
    form.order_objects = []

    #TODO Should be done in flatten_data  / FormWrapper construction
    for related in opts.get_followed_related_objects():
        wrt = related.opts.order_with_respect_to
        if wrt and wrt.rel and wrt.rel.to == opts:
            func = getattr(manipulator.original_object, 'get_%s_list' %
                    related.get_accessor_name())
            orig_list = func()
            form.order_objects.extend(orig_list)

    c = template.RequestContext(request, {
        'title': _('Change %s') % opts.verbose_name,
        'form': form,
        'object_id': object_id,
        'original': manipulator.original_object,
        'is_popup': request.REQUEST.has_key('_popup'),
    })
    return render_change_form(model, manipulator, c, change=True)


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

from django import newforms
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
# Similar to version in django.contrib.auth.forms, but this one provides
# much better security

class CciwUserEmailField(newforms.EmailField):
    def clean(self, value):
        value = super(CciwUserEmailField, self).clean(value)
        if User.objects.filter(email__iexact=value).count() == 0:
            raise newforms.ValidationError("That e-mail address doesn't have an associated user account. Are you sure you've registered?")
        return value

class PasswordResetForm(newforms.Form):
    "A form that lets a user request a password reset"
    email = CciwUserEmailField(widget=newforms.TextInput(attrs={'size':'40'}))

    def save(self, domain_override=None, email_template_name='cciw/officers/password_reset_email.txt'):
        "Calculates a new password randomly and sends it to the user"
        email = self.cleaned_data['email']
        print self.cleaned_data
        for user in User.objects.filter(email__iexact=email):
            new_pass = User.objects.make_random_password()
            current_site = Site.objects.get_current()
            site_name = current_site.name
            t = template.loader.get_template(email_template_name)
            c = {
                'new_password': new_pass,
                'email': user.email,
                'domain': current_site.domain,
                'site_name': site_name,
                'user': user,
                'hash': make_newpassword_hash(new_pass, user.username)
                }
            send_mail('Password reset on %s' % site_name, t.render(template.Context(c)), None, [user.email])

def make_newpassword_hash(newpassword, username):
    import md5
    return md5.new(settings.SECRET_KEY + newpassword + username).hexdigest()

def password_reset(request):
    template_name='cciw/officers/password_reset_form.html'
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('%sdone/' % request.path)
    else:
        form = PasswordResetForm()
    return render_to_response(template_name, {'form': form},
        context_instance=template.RequestContext(request))

# admin/password_reset_done/
def password_reset_done(request, template_name='cciw/officers/password_reset_done.html'):
    return render_to_response(template_name, context_instance=template.RequestContext(request))

def password_reset_confirm(request, template_name='cciw/officers/password_reset_confirm.html'):
    password = request.GET.get('p', '')
    username = request.GET.get('u', '')
    hash = request.GET.get('h', '')

    context_instance = template.RequestContext(request)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # Only get here if user has been deleted since email was sent.
        raise Http404
    
    if hash == make_newpassword_hash(password, username):
        context_instance['success'] = True
        user.set_password(password)
        user.save()

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

class Obj(StandardReprMixin):
    pass

def mk_objs(dictlist):
    """For each dict in dictlist, create an object based
    on the dictionary, but with any leading 'foo__' removed
    from key names."""
    retval = []
    for d in dictlist:
        obj = Obj()
        for k, v in d.iteritems():
            setattr(obj, k.split("__")[-1], v)
        retval.append(obj)
    return retval

@staff_member_required
@user_passes_test(_is_camp_admin)
def officer_list(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp
    c['invitations_all'] = camp.invitation_set.all()
    
    officers_applicationform = mk_objs(camp.application_set.filter(finished=True).values('officer__id'))
    finished_apps_off_ids = [o.id for o in officers_applicationform]
    c['officers_noapplicationform'] = mk_objs(camp.invitation_set.values('officer__id', 'officer__first_name', 'officer__last_name', 'officer__email').exclude(officer__in=finished_apps_off_ids))

    return render_to_response('cciw/officers/officer_list.html',
                              context_instance=c)
