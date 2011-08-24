from django.contrib import admin

from cciw.bookings.models import Price, BookingAccount, Booking

admin.site.register(Price)
admin.site.register(BookingAccount)
admin.site.register(Booking)
