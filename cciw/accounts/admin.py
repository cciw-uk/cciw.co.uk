from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import Role, User


class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "contact_phone_number")}),
        (
            "Permissions and roles",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "roles_display",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    filter_horizontal = []
    list_filter = ["is_staff", "is_superuser", "is_active", "roles"]
    readonly_fields = ["roles_display"]

    # Display helpers for roles
    @admin.display(description="Roles")
    def roles_display(self, obj: User):
        return ", ".join(role.name for role in obj.roles.all())


class RoleAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    ordering = ["name"]
    fields = ["name", "members", "email", "email_recipients", "allow_emails_from_public"]
    filter_horizontal = ["members", "email_recipients"]


admin.site.register(User, MyUserAdmin)
admin.site.unregister(Group)
admin.site.register(Role, RoleAdmin)
