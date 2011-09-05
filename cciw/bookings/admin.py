from django.contrib import admin
from django import forms

from cciw.bookings.models import Price, BookingAccount, Booking
from cciw.cciwmain.common import get_thisyear

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
    readonly_fields = ['total_received']


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


admin.site.register(Price, PriceAdmin)
admin.site.register(BookingAccount, BookingAccountAdmin)
admin.site.register(Booking, BookingAdmin)
