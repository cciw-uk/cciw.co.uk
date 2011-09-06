from autocomplete.fields import ModelChoiceField
from django.contrib import admin
from django import forms

from cciw.bookings.forms import FixPriceMixin
from cciw.bookings.models import Price, BookingAccount, Booking, ChequePayment
from cciw.cciwmain.common import get_thisyear
from cciw.utils.views import close_window_response

from .widgets import AccountAutoCompleteWidget

class PriceAdmin(admin.ModelAdmin):
    list_display = ['price_type', 'year', 'price']
    ordering = ['-year', 'price_type']


class BookingAccountForm(forms.ModelForm):

    class Meta:
        model = BookingAccount

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


class BookingAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'post_code', 'phone_number']
    ordering = ['email']
    search_fields = ['email', 'name']
    readonly_fields = ['first_login', 'last_login', 'total_received']
    form = BookingAccountForm

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
                   ]})
            ]
        if '_popup' not in request.GET:
            fieldsets.append(
                ('Automatically managed',
                 {'fields':
                      ['first_login',
                       'last_login',
                       'total_received',
                       ]}))
        return fieldsets

    def response_change(self, request, obj):
        # Little hack to allow popups for changing BookingAccount
        if '_popup' in request.POST:
            return close_window_response()
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


account_autocomplete_field = \
    lambda: ModelChoiceField('account',
                             label='Account',
                             widget=AccountAutoCompleteWidget('account',
                                                              attrs={'size':'70'}))

class BookingAdminForm(FixPriceMixin, forms.ModelForm):

    account = account_autocomplete_field()

    def __init__(self, *args, **kwargs):
        super(BookingAdminForm, self).__init__(*args, **kwargs)
        self.fix_price_choices()

    class Meta:
        model = Booking


class BookingAdmin(admin.ModelAdmin):
    def camp(obj):
        return "%s-%s" % (obj.camp.year, obj.camp.number)
    camp.admin_order_field = 'camp__year'
    list_display = ['name', 'sex', 'account', camp, 'state', 'confirmed_booking']
    del camp
    search_fields = ['name']
    ordering = ['-camp__year', 'camp__number']
    date_hierarchy = 'created'
    list_filter = [YearFilter, 'sex', 'price_type', 'serious_illness', 'south_wales_transport',
                   'state']

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
              ['name',
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
              ['contact_name',
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
               'amount_due',
               ]}),
        ('Internal',
         {'fields':
              ['state',
               'booking_expires',
               'created',
               'shelved']}),
        )


class ChequePaymentAdminForm(forms.ModelForm):

    account = account_autocomplete_field()

    class Meta:
        model = ChequePayment

    def clean(self):
        retval = super(ChequePaymentAdminForm, self).clean()
        if self.instance is not None and self.instance.id is not None:
            raise forms.ValidationError("Cheque payments cannot be changed "
                                        "after being created. If an error was made, "
                                        "delete this record and create a new one. ")
        return retval


class ChequePaymentAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'created']
    search_fields = ['account__name']
    date_hierarchy = 'created'
    form = ChequePaymentAdminForm
    fieldsets = [(None,
                  {'fields':
                       ['account', 'amount', 'created']})]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ['account', 'amount', 'created']
        else:
            return []


admin.site.register(Price, PriceAdmin)
admin.site.register(BookingAccount, BookingAccountAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(ChequePayment, ChequePaymentAdmin)
