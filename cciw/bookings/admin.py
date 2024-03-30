from django import forms
from django.contrib import admin, messages
from django.db.models import ManyToOneRel, Value
from django.db.models.functions import Concat
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape, escapejs, format_html

from cciw.bookings.email import send_booking_approved_mail, send_booking_confirmed_mail
from cciw.cciwmain import common
from cciw.documents.admin import DocumentAdmin, DocumentRelatedModelAdminMixin
from cciw.utils.admin import RerouteResponseAdminMixin

from .models import (
    AccountTransferPayment,
    Booking,
    BookingAccount,
    BookingState,
    CustomAgreement,
    ManualPayment,
    Payment,
    Price,
    RefundPayment,
    SupportingInformation,
    SupportingInformationDocument,
    SupportingInformationType,
    WriteOffDebt,
)

FIRST_BOOKING_YEAR = 2012


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ["price_type", "year", "price"]
    ordering = ["-year", "price_type"]


class BookingAccountForm(forms.ModelForm):
    # We need to ensure that emails that are blank get saved as
    # NULL, so that they can pass our uniqueness constraints if they are empty
    # (NULLs do not compare equal, but empty strings do)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email == "":
            email = None
        return email

    def clean(self):
        super().clean()
        if self.cleaned_data["name"] == "" and self.cleaned_data["email"] is None:
            raise forms.ValidationError("Either name or email must be defined")
        return self.cleaned_data


class ReadOnlyInline:
    # Mixin for inlines that are readonly and for display purposes only.
    # You must also set 'readonly_fields = fields' on the inline

    can_delete = False
    extra = 0
    max_num = 0

    def get_formset(self, request, obj):
        FormSet = super().get_formset(request, obj)

        class ReadOnlyFormset(FormSet):
            def is_valid(self):
                return True

            def save(self, *args, **kwargs):
                pass

            new_objects = ()
            changed_objects = ()
            deleted_objects = ()

        ReadOnlyFormset.__name__ = f"ReadOnly({FormSet.__name__})"
        return ReadOnlyFormset


# These inlines are used to display some info on BookingAccount admin
class BookingAccountPaymentInline(ReadOnlyInline, admin.TabularInline):
    model = Payment

    def link(self, payment: Payment) -> str:
        source = payment.source.model_source
        return format_html(
            '<a href="{0}" target="_blank">{1}</a>',
            reverse(f"admin:{source._meta.app_label}_{source._meta.model_name}_change", args=(source.pk,)),
            f"{source._meta.label}:{source.pk}",
        )

    fields = ["amount", "payment_type", "created_at", "link"]
    readonly_fields = fields


class BookingAccountBookingInline(ReadOnlyInline, admin.TabularInline):
    model = Booking
    label = "Confirmed bookings"

    def name(booking):
        return format_html(
            '<a href="{0}" target="_blank">{1}</a>',
            reverse("admin:bookings_booking_change", args=[booking.id]),
            booking.name,
        )

    fields = [name, "camp", "amount_due", "state", "is_confirmed"]
    readonly_fields = fields

    def get_queryset(self, *args, **kwargs):
        return (
            super()
            .get_queryset(*args, **kwargs)
            .select_related(
                "camp",
                "camp__camp_name",
                "camp__chaplain",
            )
            .prefetch_related(
                "camp__leaders",
            )
        )


class LoggedInFilter(admin.SimpleListFilter):
    title = "Ever logged in"
    parameter_name = "logged_in"

    def lookups(self, request, model_admin):
        return [
            (1, "Yes"),
            (0, "No"),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return queryset
        if val == "0":
            return queryset.filter(last_login__isnull=True)
        elif val == "1":
            return queryset.filter(last_login__isnull=False)


class BookingsYearFilter(admin.SimpleListFilter):
    title = "bookings year"
    parameter_name = "bookings_year"

    def lookups(self, request, model_admin):
        vals = range(common.get_thisyear(), FIRST_BOOKING_YEAR - 1, -1)
        return [(str(v), str(v)) for v in vals]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return queryset
        return queryset.filter(bookings__camp__year=val)


class FinalBalanceFilter(admin.SimpleListFilter):
    title = "Final balance"
    parameter_name = "final_balance"

    def lookups(self, request, model_admin):
        return [
            ("zero", "Zero"),
            ("non-zero", "Non zero"),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "zero":
            return queryset.zero_final_balance()
        elif val == "non-zero":
            return queryset.non_zero_final_balance()
        return queryset


@admin.register(BookingAccount)
class BookingAccountAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "address_post_code", "phone_number"]
    list_filter = [LoggedInFilter, BookingsYearFilter, FinalBalanceFilter, "subscribe_to_newsletter"]
    ordering = ["email"]
    search_fields = ["email", "name", "address_post_code"]
    readonly_fields = ["first_login", "last_login", "total_received", "admin_balance"]
    form = BookingAccountForm

    inlines = [
        BookingAccountPaymentInline,
        BookingAccountBookingInline,
    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                None,
                {
                    "fields": [
                        "name",
                        "email",
                        "address_line1",
                        "address_line2",
                        "address_city",
                        "address_county",
                        "address_country",
                        "address_post_code",
                        "phone_number",
                        "share_phone_number",
                        "email_communication",
                        "subscribe_to_mailings",
                        "subscribe_to_newsletter",
                    ]
                },
            )
        ]
        if "_popup" not in request.GET:
            fieldsets.append(
                (
                    "Automatically managed",
                    {
                        "fields": [
                            "first_login",
                            "last_login",
                            "total_received",
                            "admin_balance",
                        ]
                    },
                )
            )
        return fieldsets

    def get_queryset(self, request):
        # Distinct needed because of BookingsYearFilter
        return super().get_queryset(request).distinct()

    def response_change(self, request, obj):
        # Little hack to allow popups for changing BookingAccount
        if "_popup" in request.POST:
            return HttpResponse(
                "<!DOCTYPE html><html><head><title></title></head><body>"
                f'<script type="text/javascript">opener.dismissAddAnotherPopup(window, "{escape(obj._get_pk_val())}", "{escapejs(obj)}");</script></body></html>'
            )
        else:
            return super().response_change(request, obj)


class YearFilter(admin.SimpleListFilter):
    title = "camp year"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        # No easy way to create efficient query with Django's ORM,
        # so hard code first year we did bookings online:
        vals = range(common.get_thisyear(), FIRST_BOOKING_YEAR - 1, -1)
        return [(str(v), str(v)) for v in vals]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return queryset
        return queryset.for_year(val)


class ConfirmedFilter(admin.SimpleListFilter):
    title = "confirmed"
    parameter_name = "confirmed"

    def lookups(self, request, model_admin):
        return [(True, "Confirmed only")]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.confirmed()
        else:
            return queryset


class CustomAgreementFilter(admin.SimpleListFilter):
    title = "custom agreements"
    parameter_name = "agreements"

    def lookups(self, request, model_admin):
        return [
            ("0", "No missing agreements"),
            ("1", "One or more missing agreements"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "0":
            return queryset.no_missing_agreements()
        elif value == "1":
            return queryset.missing_agreements()
        else:
            return queryset


class BookingAdminForm(forms.ModelForm):
    manual_payment_amount = forms.DecimalField(label="Amount", decimal_places=2, max_digits=10, required=False)
    manual_payment_payment_type = forms.ChoiceField(
        label="Type", choices=ManualPayment._meta.get_field("payment_type").choices, required=False
    )

    class Meta:
        model = Booking
        fields = []
        fields = [
            f.name
            for f in Booking._meta.get_fields()
            if f.name not in ["erased_on"] and not isinstance(f, ManyToOneRel)
        ]


def make_change_state_action(state, display_name):
    def change_state(modeladmin, request, queryset):
        bookings = list(queryset)
        count = 0
        for booking in bookings:
            if booking.state != state:
                booking.state = state
                booking.auto_set_amount_due()
                booking.save()
                count += 1

        messages.info(request, f"Changed {count} bookings to '{display_name}'")

    change_state.short_description = f"Change to '{display_name}'"
    change_state.__name__ = f"change_state_{state}"

    return change_state


@admin.register(SupportingInformation)
class SupportingInformationAdmin(DocumentRelatedModelAdminMixin, admin.ModelAdmin):
    @admin.display(ordering="document__filename")
    def document(supporting_information):
        if supporting_information.document:
            return supporting_information.document.download_link
        return ""

    list_display = ["booking", "from_name", "information_type", document]
    autocomplete_fields = ["booking"]
    search_fields = ["booking__first_name", "booking__last_name"]
    list_select_related = ["booking__account", "booking__camp__camp_name", "information_type", "document"]
    list_filter = [YearFilter]
    date_hierarchy = "date_received"
    fields = [
        "booking",
        "information_type",
        "date_received",
        "from_name",
        "from_email",
        "from_telephone",
        "notes",
        "document",
        "erased_on",
    ]
    readonly_fields = ["erased_on"]

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).defer("document__content")


@admin.register(SupportingInformationDocument)
class SupportingInformationDocumentAdmin(DocumentAdmin):
    def booking(document):
        if hasattr(document, "supporting_information"):
            booking = document.supporting_information.booking
            return format_html(
                "<a href={0}>{1}</a>",
                reverse("admin:bookings_booking_change", kwargs=({"object_id": booking.id})),
                booking.name,
            )

    @admin.display(ordering="supporting_information__information_type__name")
    def supporting_information(document):
        if hasattr(document, "supporting_information"):
            return format_html(
                "<a href={0}>{1}</a>",
                reverse(
                    "admin:bookings_supportinginformation_change",
                    kwargs=({"object_id": document.supporting_information.id}),
                ),
                document.supporting_information.information_type.name,
            )

    list_display = DocumentAdmin.list_display + [supporting_information, booking]
    list_select_related = ["supporting_information__booking", "supporting_information__information_type"]
    list_filter = [YearFilter]
    search_fields = [
        "filename",
        "supporting_information__booking__first_name",
        "supporting_information__booking__last_name",
    ]

    readonly_fields = DocumentAdmin.readonly_fields + [supporting_information, booking]
    fields = readonly_fields


class SupportingInformationInline(DocumentRelatedModelAdminMixin, admin.StackedInline):
    model = SupportingInformation
    extra = 0
    classes = ["collapse"]
    fields = [
        "booking",
        "information_type",
        "date_received",
        "from_name",
        "from_email",
        "from_telephone",
        "notes",
        "document",
    ]

    def get_queryset(self, *args, **kwargs):
        return (
            super()
            .get_queryset(*args, **kwargs)
            .select_related(
                "information_type",
                "booking__account",
                "booking__camp__camp_name",
                "document",
            )
            .defer("document__content")
        )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    def camp(booking):
        return str(booking.camp.url_id)

    camp.admin_order_field = Concat("camp__year", Value("-"), "camp__camp_name__name")

    def confirmed(obj):
        return obj.is_confirmed

    confirmed.boolean = True

    list_display = ["first_name", "last_name", "sex", "account", camp, "state", confirmed, "created_at"]
    del camp
    del confirmed
    search_fields = ["first_name", "last_name"]
    ordering = ["-created_at"]
    list_filter = [
        YearFilter,
        "sex",
        "price_type",
        "early_bird_discount",
        "serious_illness",
        "state",
        "created_online",
        ConfirmedFilter,
        CustomAgreementFilter,
    ]
    readonly_fields = ["booked_at", "created_online"]
    autocomplete_fields = ["account"]

    form = BookingAdminForm

    inlines = [SupportingInformationInline]

    fieldsets = (
        (
            "Account",
            {
                "fields": ["account"],
            },
        ),
        ("Camp", {"fields": ["camp"]}),
        (
            "Camper details",
            {
                "fields": [
                    "first_name",
                    "last_name",
                    "sex",
                    "date_of_birth",
                    "address_line1",
                    "address_line2",
                    "address_city",
                    "address_county",
                    "address_country",
                    "address_post_code",
                    "phone_number",
                    "email",
                ]
            },
        ),
        ("Church", {"fields": ["church"]}),
        (
            "Contact details",
            {
                "fields": [
                    "contact_name",
                    "contact_line1",
                    "contact_line2",
                    "contact_city",
                    "contact_county",
                    "contact_country",
                    "contact_post_code",
                    "contact_phone_number",
                ]
            },
        ),
        ("Diet", {"fields": ["dietary_requirements"]}),
        (
            "GP details",
            {
                "fields": [
                    "gp_name",
                    "gp_line1",
                    "gp_line2",
                    "gp_city",
                    "gp_county",
                    "gp_country",
                    "gp_post_code",
                    "gp_phone_number",
                ]
            },
        ),
        (
            "Medical details",
            {
                "fields": [
                    "medical_card_number",
                    "last_tetanus_injection_date",
                    "allergies",
                    "regular_medication_required",
                    "illnesses",
                    "can_swim_25m",
                    "learning_difficulties",
                    "serious_illness",
                ]
            },
        ),
        (
            "Camper/parent agree to terms",
            {
                "fields": [
                    "agreement",
                    "publicity_photos_agreement",
                    "custom_agreements_checked",
                ]
            },
        ),
        (
            "Price",
            {
                "fields": [
                    "price_type",
                    "south_wales_transport",
                    "early_bird_discount",
                    "booked_at",
                    "amount_due",
                ]
            },
        ),
        ("Internal", {"fields": ["state", "booking_expires", "created_at", "shelved", "created_online"]}),
        ("Add a payment for account (optional)", {"fields": ["manual_payment_amount", "manual_payment_payment_type"]}),
    )

    actions = [make_change_state_action(bs, lbl) for bs, lbl in BookingState.choices]

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related("camp__camp_name")

    def save_model(self, request, obj: Booking, form, change):
        if obj.id is not None:
            old_state = Booking.objects.get(id=obj.id).state
        else:
            old_state = None
        if obj.state in [BookingState.CANCELLED_FULL_REFUND, BookingState.CANCELLED_DEPOSIT_KEPT]:
            obj.auto_set_amount_due()
        retval = super().save_model(request, obj, form, change)

        # NB: do this handling here, not in BookingAdminForm.save(),
        # because we want to make sure it is only done when the model is actually
        # saved.
        manual_amount = form.cleaned_data.get("manual_payment_amount", None)
        if manual_amount:
            obj.account.manual_payments.create(
                amount=manual_amount, payment_type=int(form.cleaned_data["manual_payment_payment_type"])
            )

        if old_state == BookingState.INFO_COMPLETE and obj.state == BookingState.APPROVED:
            email_sent = send_booking_approved_mail(obj)
            if email_sent:
                messages.info(
                    request,
                    f"An email has been sent to {obj.account.email} telling " f"them the place has been approved.",
                )
        if old_state != obj.state and obj.state == BookingState.BOOKED:
            email_sent = send_booking_confirmed_mail(obj)
            if email_sent:
                messages.info(
                    request,
                    f"A confirmation email has been sent to {obj.account.email} "
                    f"telling them the place has been booked.",
                )
        return retval


class ManualPaymentAdminBase(RerouteResponseAdminMixin, admin.ModelAdmin):
    list_display = ["account", "amount", "payment_type", "created_at"]
    search_fields = ["account__name"]
    date_hierarchy = "created_at"
    fieldsets = [(None, {"fields": ["account", "amount", "created_at", "payment_type"]})]
    autocomplete_fields = ["account"]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.fieldsets[0][1]["fields"]
        else:
            return []


@admin.register(ManualPayment)
class ManualPaymentAdmin(ManualPaymentAdminBase):
    pass


@admin.register(RefundPayment)
class RefundPaymentAdmin(ManualPaymentAdminBase):
    pass


@admin.register(WriteOffDebt)
class WriteOffDebtAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "amount", "created_at"]
    date_hierarchy = "created_at"
    search_fields = ["account__name"]
    fieldsets = [(None, {"fields": ["account", "amount", "created_at"]})]
    autocomplete_fields = ["account"]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.fieldsets[0][1]["fields"]
        else:
            return []


@admin.register(AccountTransferPayment)
class AccountTransferPaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "from_account", "to_account", "amount", "created_at"]
    date_hierarchy = "created_at"
    search_fields = ["from_account__name", "to_account__name"]
    fieldsets = [(None, {"fields": ["from_account", "to_account", "amount", "created_at"]})]
    autocomplete_fields = ["from_account", "to_account"]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.fieldsets[0][1]["fields"]
        else:
            return []


@admin.register(CustomAgreement)
class CustomAgreementAdmin(admin.ModelAdmin):
    list_display = ["name", "year", "active", "sort_order"]
    fieldsets = [(None, {"fields": ["name", "year", "text_html", "active", "sort_order"]})]


admin.site.register(SupportingInformationType)
