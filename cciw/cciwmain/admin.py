from django.contrib import admin

class SiteAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('short_name', 'long_name', 'info')}),
    )
   
class PersonAdmin(admin.ModelAdmin):
    filter_horizontal = ('users',)

class CampAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('year', 'number', 'age', 'start_date', 'end_date', 
                           'chaplain', 'leaders', 'site', 'previous_camp', 
                           'online_applications', 'admins')
                }
        ),
    )
    ordering = ['-year','number']
    list_filter = ('age', 'site', 'online_applications')
    filter_horizontal = ('leaders', 'admins')

class ForumAdmin(admin.ModelAdmin):
    pass

class NewsItemAdmin(admin.ModelAdmin):
    pass

class TopicAdmin(admin.ModelAdmin):
    list_display = ('subject', 'started_by', 'created_at')
    search_fields = ('subject',)

class GalleryAdmin(admin.ModelAdmin):
    pass

class PhotoAdmin(admin.ModelAdmin):
    pass

class PostAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'posted_by', 'posted_at')
    search_fields = ('message',)

class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'voting_starts')
    radio_fields = {'rules': admin.HORIZONTAL}

class PollOptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'poll')

class MenuLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'listorder','visible','parent_item')

class HtmlChunkAdmin(admin.ModelAdmin):
    list_display = ('name', 'page_title', 'menu_link')

class PermissionAdmin(admin.ModelAdmin):
    pass

class MemberAdmin(admin.ModelAdmin):
    search_fields = (
        'user_name', 'real_name', 'email'
    )
    list_display = (
        'user_name', 'real_name', 'email', 'date_joined', 'last_seen'
    )
    list_filter = (
        'dummy_member',
        'hidden',
        'banned',
        'moderated',
    )
    radio_fields = {'message_option': admin.HORIZONTAL}
    filter_horizontal = ('permissions',)

class AwardAdmin(admin.ModelAdmin):
    list_display = ('name', 'year')

class PersonalAwardAdmin(admin.ModelAdmin):
    list_display = ('award', 'member','reason', 'date_awarded')
    list_filter = ('award',)

class MessageAdmin(admin.ModelAdmin):
    list_display = ('to_member', 'from_member', 'time')

from cciw.cciwmain.models import Site, Person, Camp, Forum, NewsItem, Topic, Gallery, Photo, Post, Poll, PollOption, MenuLink, HtmlChunk, Permission, Member, Award, PersonalAward, Message

admin.site.register(Site, SiteAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Camp, CampAdmin)
admin.site.register(Forum, ForumAdmin)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Poll, PollAdmin)
admin.site.register(PollOption, PollOptionAdmin)
admin.site.register(MenuLink, MenuLinkAdmin)
admin.site.register(HtmlChunk, HtmlChunkAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Award, AwardAdmin)
admin.site.register(PersonalAward, PersonalAwardAdmin)
admin.site.register(Message, MessageAdmin)

