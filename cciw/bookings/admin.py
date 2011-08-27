from django.contrib import admin

from cciw.bookings.models import Price, BookingAccount, Booking


class PriceAdmin(admin.ModelAdmin):
    list_display = ['price_type', 'year', 'price']
    ordering = ['-year', 'price_type']


class BookingAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'post_code', 'phone_number']
    ordering = ['email']
    search_fields = ['email', 'name']


class YearFilter(admin.SimpleListFilter):
    title = "Year"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        vals = set(Booking.objects.values_list('camp__year', flat=True))
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
    list_display = ['name', 'sex', 'account', camp, 'state']
    del camp
    search_fields = ['name']
    ordering = ['-camp__year', 'camp__number']
    list_filter = ['sex', YearFilter]


admin.site.register(Price, PriceAdmin)
admin.site.register(BookingAccount, BookingAccountAdmin)
admin.site.register(Booking, BookingAdmin)
