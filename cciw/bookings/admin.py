from dal import autocomplete
from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape, escapejs, format_html

from cciw.bookings.email import send_booking_approved_mail, send_booking_confirmed_mail
from cciw.bookings.models import (AccountTransferPayment, Booking, BookingAccount, BookingState, ManualPayment, Payment,
                                  Price, RefundPayment)
from cciw.cciwmain import common
from cciw.utils.admin import RerouteResponseAdminMixin

FIRST_BOOKING_YEAR = 2012


bookingaccount_autocomplete_widget = lambda: autocomplete.ModelSelect2(url='bookingaccount-autocomplete')


class PriceAdmin(admin.ModelAdmin):
    list_display = ['price_type', 'year', 'price']
    ordering = ['-year', 'price_type']


class BookingAccountForm(forms.ModelForm):

    # We need to ensure that emails that are blank get saved as
    # NULL, so that they can pass our uniqueness constraints if they are empty
    # (NULLs do not compare equal, but empty strings do)

    def clean_email(self):
        email = self.cleaned_data['email']
        if email == '':
            email = None
        return email

    def clean(self):
        super(BookingAccountForm, self).clean()
        if (self.cleaned_data['name'] == '' and
                self.cleaned_data['email'] is None):
            raise forms.ValidationError("Either name or email must be defined")
        return self.cleaned_data


class ReadOnlyInline(object):
    # Mixin for inlines that are readonly and for display purposes only.
    # You must also set 'readonly_fields = fields' on the inline

    can_delete = False
    extra = 0
    max_num = 0

    def get_formset(self, request, obj):
        FormSet = super(ReadOnlyInline, self).get_formset(request, obj)

        class ReadOnlyFormset(FormSet):

            def is_valid(self):
                return True

            def save(self, *args, **kwargs):
                pass

            new_objects = ()
            changed_objects = ()
            deleted_objects = ()

        ReadOnlyFormset.__name__ = f'ReadOnly({FormSet.__name__})'
        return ReadOnlyFormset


# These inlines are used to display some info on BookingAccount admin
class BookingAccountPaymentInline(ReadOnlyInline, admin.TabularInline):
    model = Payment
    fields = ["amount", "payment_type", "created"]
    readonly_fields = fields


class BookingAccountBookingInline(ReadOnlyInline, admin.TabularInline):
    model = Booking
    label = "Confirmed bookings"

    def name(booking):
        return format_html('<a href="{0}" target="_blank">{1}</a>',
                           reverse("admin:bookings_booking_change", args=[booking.id]),
                           booking.name)
    fields = [name, "camp", "amount_due", "state", "is_confirmed"]
    readonly_fields = fields

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related(
            'camp',
            'camp__camp_name',
            'camp__chaplain',
        ).prefetch_related(
            'camp__leaders',
        )


class LoggedInFilter(admin.SimpleListFilter):
    title = "Ever logged in"
    parameter_name = "logged_in"

    def lookups(self, request, model_admin):
        return [
            (1, 'Yes'),
            (0, 'No'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return queryset
        if val == '0':
            return queryset.filter(last_login__isnull=True)
        elif val == '1':
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


class BookingAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'address_post_code', 'phone_number']
    list_filter = [LoggedInFilter, BookingsYearFilter, 'subscribe_to_newsletter']
    ordering = ['email']
    search_fields = ['email', 'name']
    readonly_fields = ['first_login', 'last_login', 'total_received', 'admin_balance']
    form = BookingAccountForm

    inlines = [BookingAccountPaymentInline,
               BookingAccountBookingInline,
               ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None,
             {'fields': ['name',
                         'email',
                         'address_line1',
                         'address_line2',
                         'address_city',
                         'address_county',
                         'address_country',
                         'address_post_code',
                         'phone_number',
                         'share_phone_number',
                         'email_communication',
                         'subscribe_to_mailings',
                         'subscribe_to_newsletter',
                         ]})
        ]
        if '_popup' not in request.GET:
            fieldsets.append(
                ('Automatically managed',
                 {'fields': ['first_login',
                             'last_login',
                             'total_received',
                             'admin_balance',
                             ]}))
        return fieldsets

    def get_queryset(self, request):
        # Distinct needed because of BookingsYearFilter
        return super(BookingAccountAdmin, self).get_queryset(request).distinct()

    def response_change(self, request, obj):
        # Little hack to allow popups for changing BookingAccount
        if '_popup' in request.POST:
            return HttpResponse(
                '<!DOCTYPE html><html><head><title></title></head><body>'
                '<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script></body></html>' %
                # escape() calls force_text.
                (escape(obj._get_pk_val()), escapejs(obj)))
        else:
            return super(BookingAccountAdmin, self).response_change(request, obj)


class YearFilter(admin.SimpleListFilter):
    title = "Year"
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
        return queryset.filter(camp__year__exact=val)


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


class BookingAdminForm(forms.ModelForm):
    manual_payment_amount = forms.DecimalField(label='Amount',
                                               decimal_places=2, max_digits=10,
                                               required=False)
    manual_payment_payment_type = forms.ChoiceField(label='Type',
                                                    choices=ManualPayment._meta.get_field('payment_type').choices,
                                                    required=False)

    class Meta:
        model = Booking
        fields = "__all__"
        widgets = {
            'account': bookingaccount_autocomplete_widget()
        }


def make_change_state_action(state, display_name):
    def change_state(modeladmin, request, queryset):
        queryset.update(state=state)
        messages.info(request, f"Changed {queryset.count()} bookings to '{display_name}'")

    change_state.short_description = f"Change to '{display_name}'"
    change_state.__name__ = f"change_state_{state}"

    return change_state


class BookingAdmin(admin.ModelAdmin):
    def camp(booking):
        return str(booking.camp.url_id)
    camp.admin_order_field = 'camp__year'

    def confirmed(obj):
        return obj.is_confirmed
    confirmed.boolean = True

    list_display = ['first_name', 'last_name', 'sex', 'account', camp, 'state', confirmed, 'created']
    del camp
    del confirmed
    search_fields = ['first_name', 'last_name']
    ordering = ['-camp__year', 'first_name', 'last_name']
    date_hierarchy = 'created'
    list_filter = [YearFilter, 'sex', 'price_type', 'early_bird_discount', 'serious_illness', 'state', 'created_online', ConfirmedFilter]
    readonly_fields = ['booked_at', 'created_online']

    form = BookingAdminForm

    fieldsets = (
        ('Account',
         {'fields':
          ['account'],
          }),
        ('Camp',
         {'fields':
          ['camp']}),
        ('Camper details',
         {'fields':
          ['first_name',
           'last_name',
           'sex',
           'date_of_birth',
           'address_line1',
           'address_line2',
           'address_city',
           'address_county',
           'address_country',
           'address_post_code',
           'phone_number',
           'email',
           ]}),
        ('Church',
         {'fields': ['church']}),
        ('Contact details',
         {'fields':
          ['contact_name',
           'contact_line1',
           'contact_line2',
           'contact_city',
           'contact_county',
           'contact_country',
           'contact_post_code',
           'contact_phone_number',
           ]}),
        ('Diet',
         {'fields':
          ['dietary_requirements']}),
        ('GP details',
         {'fields':
          ['gp_name',
           'gp_line1',
           'gp_line2',
           'gp_city',
           'gp_county',
           'gp_country',
           'gp_post_code',
           'gp_phone_number',
           ]}),
        ('Medical details',
         {'fields':
          ['medical_card_number',
           'last_tetanus_injection_date',
           'allergies',
           'regular_medication_required',
           'illnesses',
           'can_swim_25m',
           'learning_difficulties',
           'serious_illness',
           ]}),
        ('Camper/parent agree to terms',
         {'fields':
          ['agreement']}),
        ('Price',
         {'fields':
          ['price_type',
           'south_wales_transport',
           'early_bird_discount',
           'booked_at',
           'amount_due',
           ]}),
        ('Internal',
         {'fields':
          ['state',
           'booking_expires',
           'created',
           'shelved',
           'created_online']}),
        ('Add a payment for account (optional)',
         {'fields':
          ['manual_payment_amount',
           'manual_payment_payment_type']}),
    )

    actions = [
        make_change_state_action(bs, lbl)
        for bs, lbl in BookingState.choices
    ]

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related('camp__camp_name')

    def save_model(self, request, obj, form, change):
        if obj.id is not None:
            old_state = Booking.objects.get(id=obj.id).state
        else:
            old_state = None
        retval = super(BookingAdmin, self).save_model(request, obj, form, change)

        # NB: do this handling here, not in BookingAdminForm.save(),
        # because we want to make sure it is only done when the model is actually
        # saved.
        manual_amount = form.cleaned_data.get('manual_payment_amount', None)
        if manual_amount:
            obj.account.manual_payments.create(
                amount=manual_amount,
                payment_type=int(form.cleaned_data['manual_payment_payment_type']))

        if old_state == BookingState.INFO_COMPLETE and obj.state == BookingState.APPROVED:
            email_sent = send_booking_approved_mail(obj)
            if email_sent:
                messages.info(request,
                              f"An email has been sent to {obj.account.email} telling "
                              f"them the place has been approved.")
        if old_state != obj.state and obj.state == BookingState.BOOKED:
            email_sent = send_booking_confirmed_mail(obj)
            if email_sent:
                messages.info(request,
                              f"A confirmation email has been sent to {obj.account.email} "
                              f"telling them the place has been booked.")
        return retval


class ManualPaymentAdminForm(forms.ModelForm):

    class Meta:
        widgets = {
            'account': bookingaccount_autocomplete_widget()
        }


class RefundPaymentAdminForm(forms.ModelForm):

    class Meta:
        widgets = {
            'account': bookingaccount_autocomplete_widget()
        }


class ManualPaymentAdminBase(RerouteResponseAdminMixin, admin.ModelAdmin):
    list_display = ['account', 'amount', 'payment_type', 'created']
    search_fields = ['account__name']
    date_hierarchy = 'created'
    fieldsets = [(None,
                  {'fields':
                   ['account', 'amount', 'created', 'payment_type']})]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.fieldsets[0][1]['fields']
        else:
            return []


class ManualPaymentAdmin(ManualPaymentAdminBase):
    form = ManualPaymentAdminForm


class RefundPaymentAdmin(ManualPaymentAdminBase):
    form = RefundPaymentAdminForm


class AccountTransferPaymentForm(forms.ModelForm):
    class Meta:
        model = AccountTransferPayment
        fields = '__all__'
        widgets = {
            'from_account': bookingaccount_autocomplete_widget(),
            'to_account': bookingaccount_autocomplete_widget(),
        }


class AccountTransferPaymentAdmin(admin.ModelAdmin):
    form = AccountTransferPaymentForm
    list_display = ['id',
                    'from_account', 'to_account',
                    'amount', 'created']
    date_hierarchy = 'created'
    search_fields = ['from_account__name',
                     'to_account__name']

    fieldsets = [(None,
                  {'fields':
                   ['from_account', 'to_account', 'amount', 'created']})]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.fieldsets[0][1]['fields']
        else:
            return []


admin.site.register(Price, PriceAdmin)
admin.site.register(BookingAccount, BookingAccountAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(ManualPayment, ManualPaymentAdmin)
admin.site.register(RefundPayment, RefundPaymentAdmin)
admin.site.register(AccountTransferPayment, AccountTransferPaymentAdmin)
