from django.contrib import admin

from .models import EmailForward


class EmailForwardAdmin(admin.ModelAdmin):
    list_display = ['address', 'enabled']
    filter_horizontal = ['recipients']

    class Meta:
        model = EmailForward


admin.site.register(EmailForward, EmailForwardAdmin)
