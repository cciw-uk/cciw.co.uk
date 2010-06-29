from django.contrib import admin
from django.core import urlresolvers
from django import forms
from django.forms.util import ErrorList
import datetime
from cciw.middleware import threadlocals
from cciw.officers.fields import ExplicitBooleanField
from cciw.officers.models import Application, Reference, Invitation, ReferenceForm
from cciw.officers import widgets, email
from cciw.utils.views import close_window_response

class ApplicationAdminModelForm(forms.ModelForm):
    def clean(self):
        app_finished = self.cleaned_data.get('finished', False)
        user = threadlocals.get_current_user()
        # We don't allow them to submit application form for a camp that is
        # past.  This stops people submitting for incorrect camps.  Also, once
        # an Application has been marked 'finished' and the camp is past, we
        # don't allow any value to be changed, to stop the possibility of
        # tampering with saved data.
        if self.instance.pk is None:
            if self.cleaned_data['camp'].is_past():
                self._errors.setdefault('camp', ErrorList()).append("You cannot submit an application form for a camp that is already finished")

        else:
            if not user.has_perm('officers.change_application'):
                # NB: next line uses 'instance' and *not* cleaned_data, since we
                # need to look at saved data, not form data.
                if self.instance.finished and self.instance.camp.is_past():
                    self._errors.setdefault('__all__', ErrorList()).append("You cannot change a submitted application form once the camp is finished.")

        # Ensure no duplicates:
        camp_id = self.cleaned_data['camp'].id
        apps = user.application_set.filter(camp=camp_id)
        if (self.instance.pk is None and apps.exists()) or \
                (self.instance.pk is not None and apps.exclude(id=self.instance.pk).exists()):
            self._errors.setdefault('__all__', ErrorList()).append("You have already submitted an application for that camp")

        if app_finished:
            # All fields decorated with 'required_field' need to be
            # non-empty
            for name, field in self.fields.items():
                if getattr(field, 'required_field', False):
                    data = self.cleaned_data.get(name)
                    if data is None or data == u"":
                        self._errors[name] = ErrorList(["This is a required field"])
        return self.cleaned_data

class ApplicationAdmin(admin.ModelAdmin):
    save_as = False
    list_display = ('full_name', 'officer', 'camp', 'finished', 'date_submitted')
    list_filter = ('finished','date_submitted')
    ordering = ('full_name',)
    search_fields = ('full_name',)
    form = ApplicationAdminModelForm

    camp_officer_application_fieldsets = (
        (None,
            {'fields': ('camp', ),
              'classes': ('wide',),}
        ),
        ('Personal info',
            {'fields': ('full_name', 'full_maiden_name', 'birth_date', 'birth_place'),
             'classes': ('applicationpersonal', 'wide')}
        ),
        ('Address',
            {'fields': ('address_firstline', 'address_town', 'address_county',
                        'address_postcode', 'address_country', 'address_tel',
                        'address_mobile', 'address_since', 'address_email'),
             'classes': ('wide',),}
        ),
        ('Previous addresses',
            {'fields': ('address2_from', 'address2_to', 'address2_address'),
             'classes': ('wide',),
             'description': """If you have lived at your current address for less than 5 years
                            please give previous address(es) with dates below. (If more than 2 addresses,
                            use the second address box for the remaining addresses with their dates)"""}
        ),
        (None,
            {'fields': ('address3_from', 'address3_to', 'address3_address'),
             'classes': ('wide',),}
        ),
        ('Experience',
            {'fields': ('christian_experience',),
             'classes': ('wide',),
             'description': '''Please tells us about your Christian experience
                (i.e. how you became a Christian and how long you have been a Christian,
                which Churches you have attended and dates, names of minister/leader)'''}

        ),
        (None,
            {'fields': ('youth_experience',),
             'classes': ('wide',),
             'description': '''Please give details of previous experience of
                looking after or working with children/young people -
                include any qualifications or training you have. '''}
        ),
        (None,
            {'fields': ('youth_work_declined', 'youth_work_declined_details'),
             'classes': ('wide',),
             'description': 'If you have ever had an offer to work with children/young people declined, you must declare it below and give details.'}
        ),
        ('Illnesses',
            {'fields': ('relevant_illness', 'illness_details'),
             'classes': ('wide',) }
        ),
        ('Employment history',
            {'fields': ('employer1_name', 'employer1_from', 'employer1_to',
                        'employer1_job', 'employer1_leaving', 'employer2_name',
                        'employer2_from', 'employer2_to', 'employer2_job',
                        'employer2_leaving',),
             'classes': ('wide',),
              'description': 'Please tell us about your past and current employers below (if applicable)'}
        ),
        ('References',
            {'fields': ('referee1_name', 'referee1_address', 'referee1_tel', 'referee1_mobile', 'referee1_email',
                        'referee2_name', 'referee2_address', 'referee2_tel', 'referee2_mobile', 'referee2_email',),
             'classes': ('wide',),
             'description': '''Please give the names and addresses,
                telephones numbers and e-mail addresses and role or
                relationship of <strong>two</strong> people who know you
                well and who would be able to give a personal character reference.
                In addition we reserve the right to take up additional character
                references from any other individuals deemed necessary. <strong>One
                reference must be from a Church leader. The other reference should
                be from someone who has known you for more than 5 years.</strong>'''}
        ),
        ('Declarations (see note below)',
            {'fields': ('crime_declaration', 'crime_details'),
             'classes': ('wide',),
             'description': '''Note: The disclosure of an offence may not
                prohibit your appointment'''},
        ),
        (None,
            {'fields': ('court_declaration', 'court_details'),
             'classes': ('wide',), }
        ),
        (None,
            {'fields': ('concern_declaration', 'concern_details'),
             'classes': ('wide',) }
        ),
        (None,
            {'fields': ('allegation_declaration',),
             'classes': ('wide',),
             'description': '''If you answer yes to the following question
                we will need to discuss this with you''' }
        ),
        (None,
            {'fields': ('crb_check_consent',),
             'classes': ('wide',),
             'description': '''If you answer NO  to
                the following question we regret that we
                cannot proceed with your application. ''' }
        ),
        ("Confirmation",
            {'fields': ('finished',),
             'classes': ('wide',),
             'description': """By ticking this box and pressing save, you confirm
             that the information you have submitted is correct and complete, and your
             information will then be sent to the camp leader.  By leaving this box un-ticked,
             you can save what you have done so far and edit it later."""
             }
        ),
    )

    camp_leader_application_fieldsets = (
        (None,
            {'fields': ('officer',),
              'classes': ('wide',),}
        ),) + camp_officer_application_fieldsets

    def get_fieldsets(self, request, obj=None):
        user = request.user
        if user is None or user.is_anonymous():
            # never get here normally
            return ()
        else:
            if user.has_perm('officers.change_application'):
                return self.camp_leader_application_fieldsets
            else:
                return self.camp_officer_application_fieldsets

    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance(db_field, ExplicitBooleanField):
            defaults = {'widget': widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super(ApplicationAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def _update_timestamp(self, request):
        request.POST['date_submitted'] = datetime.datetime.today()
        request.POST['date_submitted_0'] = datetime.date.today()
        request.POST['date_submitted_1'] = datetime.datetime.now().strftime("%H:%M:%S")

    def _force_no_add_another(self, request):
        if request.POST.has_key('_addanother'):
            del request.POST['_addanother']

    def _force_user_val(self, request):
        user = request.user
        if not user.has_perm('officers.change_application'):
            request.POST['officer'] = unicode(request.user.id)
        else:
            # The leader possibly forgot to set the 'user' box while submitting
            # their own application form.
            if request.POST['officer'] == '':
                request.POST['officer'] = unicode(request.user.id)

    def _force_post_vals(self, request):
        request.POST = request.POST.copy()
        self._force_no_add_another(request)
        self._force_user_val(request)
        self._update_timestamp(request)

    # Officers do not even have 'officers.add_application' permission
    # - this is to prevent them adding things via the normal interface.
    # So we special case things in the permission methods

    def add_view(self, request):
        if request.method == "POST":
            self._force_post_vals(request)

        return super(ApplicationAdmin, self).add_view(request)

    def change_view(self, request, obj_id):
        if request.method == "POST":
            self._force_post_vals(request)

        return super(ApplicationAdmin, self).change_view(request, obj_id)

    def has_add_permission(self, request):
        if request.user is not None and request.user.groups.filter(name='Officers').exists():
            return True
        else:
            return super(ApplicationAdmin, self).has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Normal users do not have change permission, unless they are editing
        # their own object.  For officers, this method will return False when
        # adding a new object (which we have to fix elsewhere), and for the case
        # of listing all objects (which is what we want)
        if (obj is not None
            and (obj.officer_id is not None and obj.officer_id == request.user.id)):
            return True
        return super(ApplicationAdmin, self).has_change_permission(request, obj)

    def _redirect(self, request, response):
        if not request.POST.has_key('_continue') and response.has_header("Location"):
            location = request.GET.get('_redirect_to',
                                       urlresolvers.reverse('cciw.officers.views.applications'))
            response["Location"] = location
        return response

    def response_add(self, request, new_object):
        resp = super(ApplicationAdmin, self).response_add(request, new_object)
        return self._redirect(request, resp)

    def response_change(self, request, new_object):
        resp = super(ApplicationAdmin, self).response_change(request, new_object)
        return self._redirect(request, resp)

    def save_model(self, request, obj, form, change):
        super(ApplicationAdmin, self).save_model(request, obj, form, change)
        email.send_application_emails(request, obj)

class ReferenceAdmin(admin.ModelAdmin):
    search_fields = ['application__officer__first_name', 'application__officer__last_name']

class InvitationAdmin(admin.ModelAdmin):
    list_display = ['officer', 'camp']
    list_filter = ['camp']
    search_fields = ['officer__first_name', 'officer__last_name', 'officer__username']

class ReferenceFormAdmin(admin.ModelAdmin):
    save_as = False
    list_display = ('referee_name', 'applicant_name', 'date_created')
    ordering = ('referee_name', )
    search_fields = ('referee_name','reference_info__application__officer__last_name', 'reference_info__application__officer__first_name')

    fieldsets = (
        (None,
            {'fields': ('referee_name',
                        'how_long_known',
                        'capacity_known',
                        'known_offences',
                        'known_offences_details',
                        'capability_children',
                        'character',
                        'concerns',
                        'comments',
                        'date_created',
                        'reference_info',
                        ),
              'classes': ('wide',),}
        ),
     )
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'known_offences':
            defaults = {'widget': widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super(ReferenceFormAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def response_change(self, request, obj):
        # Little hack to allow popups for changing ReferenceForms
        if '_popup' in request.POST:
            return close_window_response()
        else:
            return super(ReferenceFormAdmin, self).response_change(request, obj)

admin.site.register(Application, ApplicationAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ReferenceForm, ReferenceFormAdmin)
