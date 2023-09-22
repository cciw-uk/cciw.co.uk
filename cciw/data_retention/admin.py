from django.contrib import admin

from cciw.data_retention.models import ErasureExecutionLog


@admin.register(ErasureExecutionLog)
class EraseExecutionLogAdmin(admin.ModelAdmin):
    list_display = ["id", "executed_at", "executed_by"]
    readonly_fields = ["plan_details", "executed_by", "executed_at"]

    def has_delete_permission(self, request, obj=None):
        # Disable delete
        return False

    def has_change_permission(self, request, obj=None):
        # Disable delete
        return False
