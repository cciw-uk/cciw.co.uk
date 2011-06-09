from cciw.cciwmain.models import Site, Person, Camp, MenuLink, HtmlChunk
from django.contrib import admin

class SiteAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('short_name', 'long_name', 'info')}),
    )

class PersonAdmin(admin.ModelAdmin):
    filter_horizontal = ('users',)

class CampAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Public info',
         {'fields': ('year', 'number', 'age', 'start_date', 'end_date',
                     'chaplain', 'leaders', 'site', 'previous_camp')
          }
        ),
        ('Applications and references',
         {'fields': ('online_applications', 'admins'),
          'description': '<div>Options for managing applications. Officer lists are managed <a href="/officers/leaders/">elsewhere</a>, not here.</div>',
          }
         ),
    )
    ordering = ('-year','number')
    def leaders(camp):
        return camp.leaders_formatted
    def chaplain(camp):
        return camp.chaplain
    chaplain.admin_order_field = 'chaplain__name'
    list_display = ('year', 'number', leaders, chaplain, 'age', 'site', 'start_date')
    list_display_links = ('number', leaders)
    del leaders, chaplain
    list_filter = ('age', 'site')
    filter_horizontal = ('leaders', 'admins')
    date_hierarchy = 'start_date'

class MenuLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'listorder','visible','parent_item')

class HtmlChunkAdmin(admin.ModelAdmin):
    list_display = ('name', 'page_title', 'menu_link')

admin.site.register(Site, SiteAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Camp, CampAdmin)
admin.site.register(MenuLink, MenuLinkAdmin)
admin.site.register(HtmlChunk, HtmlChunkAdmin)

from django.contrib.auth import admin
