from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.views.main import add_stage, render_change_form
from django.contrib.admin.views.main import unquote, quote, get_text_list
from django import forms, template
from django.http import Http404, HttpResponseRedirect
from django.db import models
from cciw.officers.models import Application
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import never_cache

# /officers/admin/
@staff_member_required
@never_cache
def index(request):
    """Displays a list of links/buttons for various actions."""
    user = request.user
    context = template.RequestContext(request)
    context['finished_applications'] = user.application_set.filter(finished=True) # TODO filtering
    context['unfinished_applications'] = user.application_set.filter(finished=False) # TODO filtering
    
    if request.POST.has_key('edit'):
        id = request.POST.get('edit_application', None)
        if id is not None:
            return HttpResponseRedirect('/admin/officers/application/%s/' % id)
    elif request.POST.has_key('new'):
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
            new_obj = Application(id=None)
            for field in Application._meta.fields:
                if field.attname != 'id':
                    setattr(new_obj, field.attname, getattr(obj, field.attname))
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
            return HttpResponseRedirect('/admin/officers/application/%s/' % new_obj.id)

    return render_to_response('cciw/officers/index', context_instance=context)


# /admin/officers/application/add/
@staff_member_required
def add_application(request):
    return add_stage(request, "officers", "application", show_delete=False, 
        form_url='', post_url="/officers/", post_url_continue='../%s/')


# /admin/officers/application/%s/

# Copied straight from django.contrib.admin.views.main,
# with small mods 
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

    if request.POST:
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
            LogEntry.objects.log_action(request.user.id, ContentType.objects.get_for_model(model).id, pk_value, str(new_object), CHANGE, change_message)

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

