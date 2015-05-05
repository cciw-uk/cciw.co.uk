from cciw.forums.models import Forum, NewsItem, Topic, Gallery, Photo, Post, Poll, PollOption, Permission, Member, Award, PersonalAward, Message
from django.contrib import admin


class ForumAdmin(admin.ModelAdmin):
    pass


class NewsItemAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_at', 'created_by')


class TopicAdmin(admin.ModelAdmin):
    list_display = ('subject', 'started_by', 'created_at')
    search_fields = ('subject',)
    date_hierarchy = 'created_at'


class GalleryAdmin(admin.ModelAdmin):
    pass


class PhotoAdmin(admin.ModelAdmin):
    pass


class PostAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'posted_by', 'posted_at')
    search_fields = ('message',)
    date_hierarchy = 'posted_at'


class PollOptionInline(admin.TabularInline):
    model = PollOption


class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'voting_starts')
    radio_fields = {'rules': admin.HORIZONTAL}
    inlines = [
        PollOptionInline,
    ]


class PollOptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'poll')


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
    list_display = ('award', 'member', 'reason', 'date_awarded')
    list_filter = ('award',)


class MessageAdmin(admin.ModelAdmin):
    list_display = ('to_member', 'from_member', 'time')


admin.site.register(Forum, ForumAdmin)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Poll, PollAdmin)
admin.site.register(PollOption, PollOptionAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Award, AwardAdmin)
admin.site.register(PersonalAward, PersonalAwardAdmin)
admin.site.register(Message, MessageAdmin)
