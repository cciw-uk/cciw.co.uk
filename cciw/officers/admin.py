import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.forms.utils import ErrorList
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.html import format_html

from cciw.cciwmain.models import Camp
from cciw.middleware import threadlocals
from cciw.officers import widgets
from cciw.officers.fields import ExplicitBooleanField
from cciw.officers.models import (
    REFEREE_DATA_FIELDS,
    REFEREE_NUMBERS,
    Application,
    CampRole,
    DBSActionLog,
    DBSCheck,
    Invitation,
    Qualification,
    QualificationType,
    Referee,
    Reference,
)
from cciw.utils.admin import RerouteResponseAdminMixin
from cciw.utils.views import close_window_response


def referee_field(n, f):
    """
    Returns the name of the referee field on Application form
    for Referee field `f`, Referee number `n`
    """
    return f"referee{n}_{f}"


class ApplicationAdminModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        try:
            initial = kwargs["initial"]
        except KeyError:
            initial = {}
            kwargs["initial"] = initial

        if "instance" not in kwargs:
            # Set some initial values for new form

            # Set officer
            user = threadlocals.get_current_user()
            if user is not None:
                # Setting 'officer' is needed when leaders/admins are using the form
                # to fill in their own application form, rather than editing someone
                # else's.
                initial["officer"] = user
                # Fill out officer name
                initial["full_name"] = user.full_name
                initial["address_email"] = user.email

        else:
            instance = kwargs["instance"]
            for n in REFEREE_NUMBERS:
                for f in REFEREE_DATA_FIELDS:
                    initial[referee_field(n, f)] = getattr(instance.referees[n - 1], f)

        super().__init__(*args, **kwargs)

    def clean(self):
        # Import here to avoid cycle
        from cciw.officers.applications import thisyears_applications

        app_finished = self.cleaned_data.get("finished", False)
        user = threadlocals.get_current_user()
        if user.can_manage_application_forms:
            officer = self.cleaned_data.get("officer", None)
        else:
            officer = self.instance.officer

        editing_old = self.instance.pk is not None and self.instance.finished
        if editing_old and not user.can_manage_application_forms:
            # Once an Application has been marked 'finished' we don't allow any
            # value to be changed, to stop the possibility of tampering with saved
            # data.
            self._errors.setdefault("__all__", ErrorList()).append("You cannot change a submitted application form.")

        future_camps = Camp.objects.filter(start_date__gte=datetime.date.today())

        self.editing_old = editing_old

        if not editing_old:
            if len(future_camps) == 0:
                self._errors.setdefault("__all__", ErrorList()).append(
                    "You cannot submit an application form until the upcoming camps are decided on."
                )

            else:
                thisyears_apps = thisyears_applications(officer)
                if self.instance.pk is not None:
                    thisyears_apps = thisyears_apps.exclude(id=self.instance.pk)
                if thisyears_apps.exists():
                    self._errors.setdefault("__all__", ErrorList()).append(
                        "You've already submitted an application form this year."
                    )

        if editing_old:
            # Ensure we don't overwrite this
            self.cleaned_data["date_saved"] = self.instance.date_saved

        if app_finished:
            # All fields decorated with 'required_field' need to be
            # non-empty
            for name, field in self.fields.items():
                if getattr(field, "required_field", False):
                    data = self.cleaned_data.get(name)
                    if data is None or data == "":
                        self._errors[name] = ErrorList(["This is a required field"])
        return self.cleaned_data

    def save(self, **kwargs):
        if not self.editing_old:
            self.instance.date_saved = datetime.date.today()
        retval = super().save(**kwargs)
        for n in REFEREE_NUMBERS:
            ref = self.instance.referees[n - 1]
            for f in REFEREE_DATA_FIELDS:
                setattr(ref, f, self.cleaned_data[referee_field(n, f)])
            ref.save()

        return retval


for f in REFEREE_DATA_FIELDS:
    for n in REFEREE_NUMBERS:
        field = Referee._meta.get_field(f).formfield()
        if f == "name":
            field.label = f"Referee {n} name"
        ApplicationAdminModelForm.base_fields[referee_field(n, f)] = field


class QualificationInline(admin.TabularInline):
    model = Qualification

    def has_add_permission(self, request, obj=None):
        if request.user.is_potential_camp_officer:
            return True
        else:
            return super().has_add_permission(request, obj=obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_potential_camp_officer and (obj is None or obj.officer_id == request.user.id):
            return True
        else:
            return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_potential_camp_officer and (obj is None or obj.officer_id == request.user.id):
            return True
        else:
            return super().has_delete_permission(request, obj)


class CampAdminPermissionMixin:
    # NB also CciwAuthBackend
    def has_change_permission(self, request, obj=None):
        if request.user.can_manage_application_forms:
            return True
        return super().has_change_permission(request, obj)


class ApplicationAdmin(CampAdminPermissionMixin, admin.ModelAdmin):
    save_as = False

    def officer_username(self, obj):
        return obj.officer.username

    officer_username.admin_order_field = "officer__username"
    officer_username.short_description = "username"
    list_display = ["full_name", "officer_username", "address_email", "finished", "date_saved"]
    list_filter = ["finished", "date_saved"]
    ordering = ["full_name"]
    search_fields = ["full_name"]
    readonly_fields = ["date_saved"]
    date_hierarchy = "date_saved"
    form = ApplicationAdminModelForm

    camp_officer_application_fieldsets = [
        (
            "Personal info",
            {"fields": ["full_name", "birth_date", "birth_place"], "classes": ["applicationpersonal", "wide"]},
        ),
        (
            "Address",
            {
                "fields": [
                    "address_firstline",
                    "address_town",
                    "address_county",
                    "address_postcode",
                    "address_country",
                    "address_tel",
                    "address_mobile",
                    "address_email",
                ],
                "classes": ["wide"],
                "description": "We will use this information to send you information about camp, "
                "and for other necessary purposes such as DBS checks.",
            },
        ),
        (
            "Experience",
            {
                "fields": ["christian_experience"],
                "classes": ["applicationexperience", "wide"],
                "description": """Please tells us about your Christian experience """
                """(i.e. how you became a Christian and how long you have been a Christian, """
                """which Churches you have attended and dates, names of minister/leader)""",
            },
        ),
        (
            None,
            {
                "fields": ["youth_experience"],
                "classes": ["wide"],
                "description": """Please give details of previous experience of """
                """looking after or working with children/young people - """
                """include any qualifications or training you have. """,
            },
        ),
        (
            None,
            {
                "fields": ["youth_work_declined", "youth_work_declined_details"],
                "classes": ["wide"],
                "description": "If you have ever had an offer to work with children/young people declined, you must declare it below and give details.",
            },
        ),
        (
            "Health",
            {
                "fields": ["relevant_illness", "illness_details", "dietary_requirements"],
                "classes": ["applicationillness", "wide"],
            },
        ),
        (
            "References",
            {
                "fields": [referee_field(n, f) for n in REFEREE_NUMBERS for f in REFEREE_DATA_FIELDS],
                "classes": ["wide"],
                "description": """Please give the names and addresses,
             telephones numbers and email addresses of <strong>two</strong> people who know you
             well and who would be able to give a personal character reference.
             In addition we reserve the right to take up additional character
             references from any other individuals deemed necessary. <strong>One
             reference must be from a Church leader. The other reference should
             be from someone who has known you for more than 3 years.</strong>""",
            },
        ),
        (
            "Declarations (see note below)",
            {
                "fields": ["crime_declaration", "crime_details"],
                "classes": ["wide"],
                "description": """Note: The disclosure of an offence may not
                prohibit your appointment""",
            },
        ),
        (None, {"fields": ["court_declaration", "court_details"], "classes": ["wide"]}),
        (None, {"fields": ["concern_declaration", "concern_details"], "classes": ["wide"]}),
        (
            None,
            {
                "fields": ["allegation_declaration"],
                "classes": ["wide"],
                "description": """If you answer yes to the following question
                we will need to discuss this with you""",
            },
        ),
        (
            "DBS checks",
            {
                "fields": ["dbs_number", "dbs_check_consent"],
                "classes": ["wide"],
                "description": format_html(
                    """
<h3>Important information, please read:</h3>

<p>You need to give permission for us to obtain a DBS check for you. Otherwise
we regret that we cannot proceed with your application.</p>

<p>If you have a current enhanced Disclosure and Barring Service check <b>and have
signed up for the update system</b>, and if you give permission for CCiW to look at
it, please enter the certificate number below.</p>

<p>If we need a new DBS check for you, once your application form is received a
DBS application form will be sent to you, so please ensure your postal address
is up to date. The DBS form must be filled in and all instructions adhered to.
The DBS check will be carried out by {0}.
<b>By CCiW policy, failure to do so will mean that you will be unable to come on
camp.</b></p>

<p><b>Please also note</b> the instructions to sign up for the <b>update
service</b>. This will save you and everyone else a lot of time in subsequent
years. You will receive an e-mail from DBS with a reference number and at the
bottom of the e-mail are details of signing up for the update service. THIS MUST
BE DONE WITHIN 19 DAYS of the issue of the DBS. Otherwise after 3 years you will
have to fill in another DBS form.</p> """,
                    settings.EXTERNAL_DBS_OFFICER["organisation_long"],
                ),
            },
        ),
        (
            "Confirmation",
            {
                "fields": ("finished",),
                "classes": ("wide", "confirmation"),
                "description": """<div>By ticking the following box and pressing save, you confirm
             that:</div>
             <ol>
             <li>the information you have submitted is <strong>correct and complete</strong>,</li>
             <li>you have <strong>read and understood</strong> the relevant sections of the officers
                handbook. These include:

             <ul>
             <li><a target="_blank" href="/officers/files/handbook/Intro%20-%20CCiW%20Safe%20From%20Harm%20Policy.pdf">Intro - CCiW Safe From Harm Policy</a></li>
             <li><a target="_blank" href="/officers/files/handbook/1.%20Officers%20Handbook.pdf">1. Officers Handbook</a></li>
             <li><a target="_blank" href="/officers/files/handbook/2.%20Guidance%20for%20Leaders%20and%20Chaplains.pdf">2. Guidance for Leaders and Chaplains</a></li>
             <li><a target="_blank" href="/officers/files/handbook/3.%20Guidance%20for%20Medical%20and%20First%20Aid.pdf">3. Guidance for Medical and First Aid</a></li>
             <li><a target="_blank" href="/officers/files/handbook/4.%20Guidance%20for%20Site%20and%20Maintenance.pdf">4. Guidance for Site and Maintenance</a></li>
             <li><a target="_blank" href="/officers/files/handbook/5.%20Guidance%20for%20Minibus%20Drivers.pdf">5. Guidance for Minibus Drivers</a></li>
             <li><a target="_blank" href="/officers/files/handbook/6.%20Identifying%20and%20Responding%20to%20Child%20Abuse.pdf">6. Identifying and Responding to Child Abuse</a></li>
             <li><a target="_blank" href="/officers/files/handbook/7.%20Catering%20Manual.pdf">7. Catering Manual</a></li>
             <li><a target="_blank" href="/officers/files/handbook/8.%20Doctrinal%20Basis.pdf">8. Doctrinal Basis</a></li>
             </ul>

             <div>The following sections are required:</div>
             <ul>
             <li>All officers must read “Intro - CCiW Safe From Harm Policy”</li>
             <li>Officers should all be familiar with Appendices 1, 6 and 8.</li>
             <li>Kitchen Leaders and Helpers should be familiar with Appendices 1, 6, 7 & 8</li>
             <li>Officers and Helpers requested to provide medical assistance or first aid should be familiar with Appendix 3.</li>
             <li>Site Leaders and Helpers should be familiar with Appendices 1, 4, 6 & 8.</li>
             <li>Officers and Helpers requested to drive minibuses should be familiar with Appendix 5.</li>
             <li>Directors, Leaders, Assistant Leaders and Chaplains should be familiar with all of the Appendices</li>

             </ul>
             <li>you permit CCiW to store this information and the references and DBS checks that
             we will collect for as long as necessary.</li>
             </ol>
             <div>Your information will then be sent to the camp leader.  By leaving this
             box un-ticked, you can save what you have done so far and edit it later.</div>""",
            },
        ),
    ]

    camp_leader_application_fieldsets = [
        (None, {"fields": ["officer", "date_saved"], "classes": ["wide"]})
    ] + camp_officer_application_fieldsets
    autocomplete_fields = ["officer"]

    inlines = [QualificationInline]

    class Media:
        js = ["js/application_form.js"]

    def get_fieldsets(self, request, obj=None):
        user = request.user
        if user is None or user.is_anonymous:
            # never get here normally
            return ()
        else:
            if user.can_manage_application_forms:
                return self.camp_leader_application_fieldsets
            else:
                return self.camp_officer_application_fieldsets

    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance(db_field, ExplicitBooleanField):
            defaults = {"widget": widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super().formfield_for_dbfield(db_field, **kwargs)

    def _force_no_add_another(self, request):
        if "_addanother" in request.POST:
            del request.POST["_addanother"]

    def _force_user_val(self, request):
        user = request.user
        if not user.can_manage_application_forms:
            request.POST["officer"] = str(request.user.id)
        else:
            # The leader possibly forgot to set the 'user' box while submitting
            # their own application form.
            if request.POST.get("officer", "") == "":
                request.POST["officer"] = str(request.user.id)

    def _force_post_vals(self, request):
        request.POST = request.POST.copy()
        self._force_no_add_another(request)
        self._force_user_val(request)

    def change_view(self, request, object_id: str):
        if request.method == "POST":
            self._force_post_vals(request)

        return super().change_view(request, object_id, extra_context={"is_nav_sidebar_enabled": False})

    def has_change_permission(self, request, obj=None):
        # Normal users do not have change permission, unless they are editing
        # their own object.  For officers, this method will return False when
        # adding a new object (which we have to fix elsewhere), and for the case
        # of listing all objects (which is what we want)
        if obj is not None and (obj.officer_id is not None and obj.officer_id == request.user.id):
            return True
        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj=obj)

    def _redirect(self, request, response):
        if "_continue" not in request.POST and response.has_header("Location"):
            location = request.GET.get("_redirect_to", reverse("cciw-officers-applications"))
            response["Location"] = location
        return response

    def response_change(self, request, new_object):
        resp = super().response_change(request, new_object)
        return self._redirect(request, resp)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.finished and obj.officer == request.user:
            # We clear out any unfinished application forms, as they will just
            # confuse the officer in future.
            obj.clear_out_old_unfinished()

    def save_related(self, request, form, formsets, change):
        from cciw.officers import email

        super().save_related(request, form, formsets, change)
        email.send_application_emails(request, form.instance)


class InvitationAdmin(admin.ModelAdmin):
    list_display = ["officer", "camp", "notes", "date_added"]
    list_filter = ["camp"]
    search_fields = ["officer__first_name", "officer__last_name", "officer__username"]

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).prefetch_related("camp__leaders")


class ReferenceAdmin(CampAdminPermissionMixin, admin.ModelAdmin):
    save_as = False
    list_display = ["referee_name", "applicant_name", "date_created"]
    ordering = ["referee_name"]
    search_fields = [
        "referee_name",
        "referee__application__officer__last_name",
        "referee__application__officer__first_name",
    ]
    date_hierarchy = "date_created"
    raw_id_fields = ["referee"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "referee_name",
                    "how_long_known",
                    "capacity_known",
                    "known_offences",
                    "known_offences_details",
                    "capability_children",
                    "character",
                    "concerns",
                    "comments",
                    "given_in_confidence",
                    "date_created",
                    "referee",
                ],
                "classes": ["wide"],
            },
        ),
    ]

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "known_offences":
            defaults = {"widget": widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super().formfield_for_dbfield(db_field, **kwargs)

    def response_change(self, request, obj) -> HttpResponse:
        # Little hack to allow popups for changing References
        if "_popup" in request.POST:
            return close_window_response(request)
        else:
            return super().response_change(request, obj)


class DBSCheckAdmin(RerouteResponseAdminMixin, admin.ModelAdmin):

    search_fields = ["officer__first_name", "officer__last_name", "dbs_number"]
    list_display = ["first_name", "last_name", "dbs_number", "completed", "requested_by", "registered_with_dbs_update"]
    list_display_links = ("first_name", "last_name", "dbs_number")
    list_filter = ["requested_by", "registered_with_dbs_update", "check_type"]
    ordering = ("-completed",)
    date_hierarchy = "completed"
    autocomplete_fields = ["officer"]

    def first_name(self, obj):
        return obj.officer.first_name

    first_name.admin_order_field = "officer__first_name"

    def last_name(self, obj):
        return obj.officer.last_name

    last_name.admin_order_field = "officer__last_name"


class DBSActionLogAdmin(admin.ModelAdmin):

    search_fields = ("officer__first_name", "officer__last_name")
    list_display = ["action_type", "first_name", "last_name", "created_at", "user"]
    list_display_links = ["action_type"]
    list_filter = ["action_type"]
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    autocomplete_fields = ["officer", "user"]

    def first_name(self, obj):
        return obj.officer.first_name

    first_name.admin_order_field = "officer__first_name"

    def last_name(self, obj):
        return obj.officer.last_name

    last_name.admin_order_field = "officer__last_name"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("officer", "user")


admin.site.register(Application, ApplicationAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(DBSCheck, DBSCheckAdmin)
admin.site.register(DBSActionLog, DBSActionLogAdmin)
admin.site.register(QualificationType)
admin.site.register(CampRole)
