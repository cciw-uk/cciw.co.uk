from django.contrib import admin

from cciw.contact_us.models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "booking_account", "name", "created_at"]
    autocomplete_fields = ["booking_account"]


admin.site.register(Message, MessageAdmin)
