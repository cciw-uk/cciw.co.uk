from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import Role, User


@admin.register(User)
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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    ordering = ["name"]

    @admin.display(description="Member's emails")
    def members_emails(self, obj: Role):
        return ", ".join(member.email for member in obj.members.all())

    fields = ["name", "members", "email", "email_recipients", "allow_emails_from_public", "members_emails"]
    readonly_fields = ["members_emails"]
    filter_horizontal = ["members", "email_recipients"]


admin.site.unregister(Group)
