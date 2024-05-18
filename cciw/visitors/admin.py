from django.contrib import admin

from cciw.visitors.models import VisitorLog


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ["guest_name", "camp", "arrived_on", "purpose_of_visit"]
    readonly_fields = ["logged_at", "logged_by", "remote_addr"]
    search_fields = ["guest_name"]
    ordering = ("-logged_at",)
    date_hierarchy = "arrived_on"
