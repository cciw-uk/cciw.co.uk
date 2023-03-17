from django.contrib import admin, messages
from django.db.models.query import QuerySet
from django.template.defaultfilters import linebreaksbr
from django.urls.base import reverse
from django.utils.html import format_html

from cciw.contact_us.models import Message


@admin.action(description="Mark selected messages as spam")
def mark_spam(modeladmin, request, queryset: QuerySet[Message]):
    for message in queryset:
        message.mark_spam()
    messages.info(request, f"{len(queryset)} messages marked as spam")


@admin.action(description="Mark selected messages as ham")
def mark_ham(modeladmin, request, queryset: QuerySet[Message]):
    for message in queryset:
        message.mark_ham()
    messages.info(request, f"{len(queryset)} messages marked as ham")


@admin.action(description="Classify using bogofilter")
def classify_with_bogofilter(modeladmin, request, queryset: QuerySet[Message]):
    for message in queryset:
        message.classify_with_bogofilter()
    messages.info(request, f"{len(queryset)} messages classified using bogofilter")


class MessageAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("booking_account")

    def view(message):
        url = reverse("cciw-contact_us-view", kwargs={"message_id": message.id})
        return format_html(f"""<a href='{url}'>View {message.id}</a>""")

    @admin.display(description="Booking account")
    def booking_account(message):
        if message.booking_account:
            return format_html("{0}<br>{1}", message.booking_account.name, message.booking_account.email)
        return ""

    @admin.display(description="Message")
    def message_formatted(message):
        return linebreaksbr(message.message)

    date_hierarchy = "created_at"
    list_display = [
        "id",
        "subject",
        "email",
        booking_account,
        "name",
        message_formatted,
        "spam_classification_manual",
        "spam_classification_bogofilter",
        "created_at",
        view,
    ]
    autocomplete_fields = ["booking_account"]
    list_filter = ["subject", "spam_classification_manual", "spam_classification_bogofilter"]
    actions = [mark_spam, mark_ham, classify_with_bogofilter]


admin.site.register(Message, MessageAdmin)
