from cciw.tagging.models import Tag
from django.contrib import admin


class TagAdmin(admin.ModelAdmin):
    list_display = (
        'text',
        'target',
        'creator',
        'added',
    )
    list_filter = (
        'target_ct',
    )
    search_fields = ('text',)


admin.site.register(Tag, TagAdmin)
