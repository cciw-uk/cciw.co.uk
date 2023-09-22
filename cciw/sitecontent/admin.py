from django.contrib import admin

from cciw.sitecontent.models import HtmlChunk, MenuLink


@admin.register(MenuLink)
class MenuLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "url", "listorder", "visible", "parent_item")

    def get_queryset(self, *args):
        return super().get_queryset(*args).select_related("parent_item")


@admin.register(HtmlChunk)
class HtmlChunkAdmin(admin.ModelAdmin):
    list_display = ("name", "page_title", "menu_link")
