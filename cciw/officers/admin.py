from django.contrib import admin
from django.core import urlresolvers
from django import forms
from django.forms.util import ErrorList
import datetime
from cciw.middleware import threadlocals
from cciw.officers.fields import ExplicitBooleanField
from cciw.officers.models import Application, Reference, Invitation
from cciw.officers import widgets

class ApplicationAdminModelForm(forms.ModelForm):
    def clean(self):
        app_finished = self.cleaned_data.get('finished', False)
        user = threadlocals.get_current_user()
        # If not admin, we don't allow them to submit application form
        # for a camp that is past.
        if self.instance.pk is not None:
            if not user.has_perm('officers.change_application'):
                if self.cleaned_data['camp'].end_date < datetime.date.today():
                    self._errors.setdefault('camp', ErrorList()).append("You cannot submit an application form for a camp that is already finished")

                if self.instance.finished and (self.instance.camp != self.cleaned_data['camp']):
                    self._errors.setdefault('__all__', ErrorList()).append("You cannot change the camp once you have submitted the form")

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

    def _force_post_vals(self, request):
        request.POST = request.POST.copy()
        self._force_no_add_another(request)
        self._force_user_val(request)
        self._update_timestamp(request)

    # Officers do not even have 'officers.add_application' permission
    # - this is to prevent them adding things via the normal interface,
    # and to force certain buttons to not appear.  So we special case
    # things in the permission methods

    def add_view(self, request):
        if request.method == "POST":
            self._force_post_vals(request)

        return super(ApplicationAdmin, self).add_view(request)

    def change_view(self, request, obj_id):
        if request.method == "POST":
            self._force_post_vals(request)

        return super(ApplicationAdmin, self).change_view(request, obj_id)

    def has_add_permission(self, request):
        if request.user is not None and request.user.groups.filter(name='Officers').count() > 0:
            return True
        else:
            return super(ApplicationAdmin, self).has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Normal users do not have change permission, unless they are editing
        # their own object.
        if obj is not None and obj.officer_id is not None \
                and obj.officer_id == request.user.id:
            return True
        return super(ApplicationAdmin, self).has_change_permission(request, obj)

    def _redirect_to_officer_home_page(self, request, response):
        if not request.POST.has_key('_continue') and response.has_header("Location"):
            response["Location"] = urlresolvers.reverse('cciw.officers.views.applications')
        return response

    def response_add(self, request, new_object):
        resp = super(ApplicationAdmin, self).response_add(request, new_object)
        return self._redirect_to_officer_home_page(request, resp)

    def response_change(self, request, new_object):
        resp = super(ApplicationAdmin, self).response_change(request, new_object)
        return self._redirect_to_officer_home_page(request, resp)

class ReferenceAdmin(admin.ModelAdmin):
    search_fields = ['application__officer__first_name', 'application__officer__last_name']

class InvitationAdmin(admin.ModelAdmin):
    list_display = ['officer', 'camp']
    list_filter = ['camp']
    search_fields = ['officer']

admin.site.register(Application, ApplicationAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Invitation, InvitationAdmin)
