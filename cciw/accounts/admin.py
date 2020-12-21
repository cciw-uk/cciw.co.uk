from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import Role, User


class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None,
         {'fields': ('username', 'password')}),
        ('Personal info',
         {'fields': (
             'first_name', 'last_name', 'email', 'contact_phone_number')
          }),
        ('Permissions',
         {'fields': (
             'is_active', 'is_staff', 'is_superuser',
         )}),
        ('Important dates',
         {'fields': (
             'last_login', 'date_joined')
          }),
    )
    filter_horizontal = []
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'roles']


class RoleAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    fields = ['name', 'members', 'email', 'email_recipients']
    filter_horizontal = ['members', 'email_recipients']


admin.site.register(User, MyUserAdmin)
admin.site.unregister(Group)
admin.site.register(Role, RoleAdmin)
