from django.contrib import admin

from .models import EmailNotification


class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'timestamp', 'event']
    list_filter = ['event']
    date_hierarchy = 'timestamp'


admin.site.register(EmailNotification, EmailNotificationAdmin)
