from django.contrib import admin
from django.template.defaultfilters import linebreaksbr
from django.urls.base import reverse
from django.utils.html import format_html

from cciw.contact_us.models import Message


class MessageAdmin(admin.ModelAdmin):
    def view(message):
        url = reverse("cciw-contact_us-view", kwargs={"message_id": message.id})
        return format_html(f"""<a href='{url}'>View {message.id}</a>""")

    def message_formatted(message):
        return linebreaksbr(message.message)

    list_display = ["id", "subject", "email", "booking_account", "name", message_formatted, view, "created_at"]
    autocomplete_fields = ["booking_account"]
    list_filter = ["subject"]


admin.site.register(Message, MessageAdmin)
