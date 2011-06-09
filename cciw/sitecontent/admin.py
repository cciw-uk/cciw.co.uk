from cciw.sitecontent.models import MenuLink, HtmlChunk
from django.contrib import admin

class MenuLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'listorder','visible','parent_item')

class HtmlChunkAdmin(admin.ModelAdmin):
    list_display = ('name', 'page_title', 'menu_link')

admin.site.register(MenuLink, MenuLinkAdmin)
admin.site.register(HtmlChunk, HtmlChunkAdmin)
