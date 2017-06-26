from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . models import User


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
             'groups', 'user_permissions')
          }),
        ('Important dates',
         {'fields': (
             'last_login', 'date_joined')
          }),
    )


admin.site.register(User, MyUserAdmin)
