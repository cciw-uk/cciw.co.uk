import autocomplete_light

from django.contrib import admin
from django.contrib import messages
from django.core.urlresolvers import reverse
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import escape, escapejs, format_html
from django.utils.http import is_safe_url

from cciw.bookings.email import send_booking_approved_mail, send_booking_confirmed_mail
from cciw.bookings.models import Price, BookingAccount, Booking, ManualPayment, RefundPayment, BOOKING_APPROVED, BOOKING_INFO_COMPLETE, BOOKING_BOOKED, Payment
from cciw.cciwmain.common import get_thisyear


account_autocomplete_field = lambda: autocomplete_light.ModelChoiceField('account')


class ReturnToAdminMixin(object):
    def conditional_redirect(self, request, main_response):
        if 'return_to' in request.GET:
            url = request.GET['return_to']
            if is_safe_url(url=url, host=request.get_host()):
                return HttpResponseRedirect(url)
        return main_response

    def response_post_save_add(self, request, obj):
        return self.conditional_redirect(request,
                                         super(ReturnToAdminMixin, self).response_post_save_add(request, obj))

    def response_post_save_change(self, request, obj):
        return self.conditional_redirect(request,
                                         super(ReturnToAdminMixin, self).response_post_save_change(request, obj))


class PriceAdmin(admin.ModelAdmin):
    list_display = ['price_type', 'year', 'price']
    ordering = ['-year', 'price_type']


class BookingAccountForm(forms.ModelForm):

    # We need to ensure that email/name/post_code that are blank get saved as
    # NULL, so that they can pass our uniqueness constraints if they are empty
    # (NULLs do not compare equal, but empty strings do)

    def clean_email(self):
        email = self.cleaned_data['email']
        if email == u'':
            email = None
        return email

    def clean_name(self):
        name = self.cleaned_data['name']
        if name == u'':
            name = None
        return name

    def clean_post_code(self):
        post_code = self.cleaned_data['post_code']
        if post_code == u'':
            post_code = None
        return post_code

    def clean(self):
        super(BookingAccountForm, self).clean()
        if (self.cleaned_data['name'] == None and
            self.cleaned_data['email'] == None):
            raise forms.ValidationError("Either name or email must be defined")
        return self.cleaned_data


# These inlines are used to display some info on BookingAccount admin
class BookingAccountPaymentInline(admin.TabularInline):
    model = Payment
    fields = ["amount", "payment_type", "created"]
    readonly_fields = fields
    can_delete = False
    extra = 0
    max_num = 0


class BookingAccountBookingInline(admin.TabularInline):
    model = Booking
    label = "Confirmed bookings"
    def name(booking):
        return format_html('<a href="{0}" target="_blank">{1}</a>',
                           reverse("admin:bookings_booking_change", args=[booking.id]),
                           booking.name)
    fields = [name, "camp", "amount_due", "state", "is_confirmed"]
    readonly_fields = fields
    can_delete = False
    extra = 0
    max_num = 0


class BookingAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'post_code', 'phone_number']
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
             {'fields':
                  ['name',
                   'email',
                   'address',
                   'post_code',
                   'phone_number',
                   'share_phone_number',
                   'email_communication',
                   ]})
            ]
        if '_popup' not in request.GET:
            fieldsets.append(
                ('Automatically managed',
                 {'fields':
                      ['first_login',
                       'last_login',
                       'total_received',
                       'admin_balance',
                       ]}))
        return fieldsets

    def response_change(self, request, obj):
        # Little hack to allow popups for changing BookingAccount
        if '_popup' in request.POST:
            return HttpResponse(
                '<!DOCTYPE html><html><head><title></title></head><body>'
                '<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script></body></html>' % \
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
        vals = range(2012, get_thisyear() + 1)
        return [(str(v),str(v)) for v in vals]

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


class BookingAdminForm(autocomplete_light.ModelForm):
    manual_payment_amount = forms.DecimalField(label='Amount',
                                               decimal_places=2, max_digits=10,
                                               required=False)
    manual_payment_payment_type = forms.ChoiceField(label='Type',
                                                    choices=ManualPayment._meta.get_field('payment_type').choices,
                                                    required=False)
    class Meta:
        model = Booking
        fields = "__all__"


class BookingAdmin(admin.ModelAdmin):
    def camp(obj):
        return "%s-%s" % (obj.camp.year, obj.camp.number)
    camp.admin_order_field = 'camp__year'

    def confirmed(obj):
        return obj.is_confirmed
    confirmed.boolean = True

    list_display = ['first_name', 'last_name', 'sex', 'account', camp, 'state', confirmed, 'created']
    del camp
    search_fields = ['first_name', 'last_name']
    ordering = ['-camp__year', 'camp__number']
    date_hierarchy = 'created'
    list_filter = [YearFilter, 'sex', 'price_type', 'serious_illness', 'state', 'created_online', ConfirmedFilter]
    readonly_fields = ['booked_at', 'created_online']

    form = BookingAdminForm


    fieldsets = (
        ('Account',
         {'fields':
              ['account',
               ],
          'description': "Enter the account name, then choose from the suggestions, or choose 'New account' if there is no match. Use 'edit' to change the details of a selected account." }),
        ('Camp',
         {'fields':
              ['camp']}),
        ('Camper details',
         {'fields':
              ['first_name',
               'last_name',
               'sex',
               'date_of_birth',
               'address',
              'post_code',
               'phone_number',
               'email',
               ]}),
        ('Church',
         {'fields': ['church']}),
        ('Contact details',
         {'fields':
              ['contact_address',
               'contact_post_code',
               'contact_phone_number',
               ]}),
        ('Diet',
         {'fields':
              ['dietary_requirements']}),
        ('GP details',
         {'fields':
              ['gp_name',
               'gp_address',
               'gp_phone_number',
               ]}),
        ('Medical details',
         {'fields':
              ['medical_card_number',
               'last_tetanus_injection',
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
            obj.account.manualpayment_set.create(
                amount=manual_amount,
                payment_type=int(form.cleaned_data['manual_payment_payment_type']))

        if old_state == BOOKING_INFO_COMPLETE and obj.state == BOOKING_APPROVED:
            email_sent = send_booking_approved_mail(obj)
            if email_sent:
                messages.info(request, "An email has been sent to %s telling "
                              "them the place has been approved." % (obj.account.email))
        if old_state != obj.state and obj.state == BOOKING_BOOKED:
            email_sent = send_booking_confirmed_mail(obj)
            if email_sent:
                messages.info(request, "A confirmation email has been sent to %s "
                              "telling them the place has been booked." % obj.account.email)
        return retval


class ManualPaymentAdminFormBase(forms.ModelForm):

    account = account_autocomplete_field()

    def clean(self):
        retval = super(ManualPaymentAdminFormBase, self).clean()
        if self.instance is not None and self.instance.id is not None:
            raise forms.ValidationError("Manual payments cannot be changed "
                                        "after being created. If an error was made, "
                                        "delete this record and create a new one. ")
        return retval


class ManualPaymentAdminForm(ManualPaymentAdminFormBase):
    pass


class RefundPaymentAdminForm(ManualPaymentAdminFormBase):
    pass


class ManualPaymentAdminBase(ReturnToAdminMixin, admin.ModelAdmin):
    list_display = ['account', 'amount', 'payment_type', 'created']
    search_fields = ['account__name']
    date_hierarchy = 'created'
    fieldsets = [(None,
                  {'fields':
                       ['account', 'amount', 'created', 'payment_type']})]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ['account', 'amount', 'created', 'payment_type']
        else:
            return []


class ManualPaymentAdmin(ManualPaymentAdminBase):
    form = ManualPaymentAdminForm


class RefundPaymentAdmin(ManualPaymentAdminBase):
    form = RefundPaymentAdminForm


admin.site.register(Price, PriceAdmin)
admin.site.register(BookingAccount, BookingAccountAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(ManualPayment, ManualPaymentAdmin)
admin.site.register(RefundPayment, RefundPaymentAdmin)
