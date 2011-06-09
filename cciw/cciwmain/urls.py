from django.conf.urls.defaults import patterns, url
from django.conf import settings

# Forums and news items are tightly integrated (read: tangled) into the main
# site, and always have been, so URLs and some view code for forums are part of
# the 'cciwmain' app rather than the 'forums' app.

urlpatterns = \
patterns('cciw.cciwmain.views',
    # Members
    (r'^login/$', 'members.login'),
    url(r'^members/$', 'members.index', name="cciwmain.members.index"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail', name="cciwmain.members.detail"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/posts/$', 'members.posts', name="cciwmain.members.posts"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/$', 'members.send_message', name="cciwmain.members.send_message"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/inbox/$', 'members.inbox', name="cciwmain.members.inbox"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/archived/$', 'members.archived_messages', name="cciwmain.members.archived_messages"),
    url(r'^signup/$', 'memberadmin.signup', name="cciwmain.memberadmin.signup"),
    (r'^memberadmin/change-password/$', 'memberadmin.change_password'),
    (r'^memberadmin/change-email/$', 'memberadmin.change_email'),
    url(r'^memberadmin/preferences/$', 'memberadmin.preferences', name="cciwmain.memberadmin.preferences"),
    url(r'^help/logging-in/$', 'memberadmin.help_logging_in', name="cciwmain.memberadmin.help_logging_in"),

    # Camps
    (r'^thisyear/$', 'camps.thisyear'),
    (r'^thisyear/bookingform/$', 'misc.bookingform'),
    (r'^camps/$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', 'camps.detail'),
    (r'^' + settings.CAMP_FORUM_RE + r'$', 'camps.forum'),
    url(r'^' + settings.CAMP_FORUM_RE + r'(?P<topicnumber>\d+)/$', 'camps.topic', name='cciwmain.camps.topic'),
    (r'^' + settings.CAMP_FORUM_RE + r'add/$', 'camps.add_topic'),
    (r'^' + settings.CAMP_FORUM_RE + r'add_news/$', 'camps.add_news'),
    url(r'^' + settings.CAMP_FORUM_RE + r'add_poll/$', 'camps.edit_poll', name='cciwmain.camps.add_poll'),
    url(r'^' + settings.CAMP_FORUM_RE + r'edit_poll/(?P<poll_id>\d+)/$', 'camps.edit_poll', name='cciwmain.camps.edit_poll'),

    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', 'camps.gallery'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', 'camps.photo'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', 'camps.oldcampgallery'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', 'camps.oldcampphoto'),

    # Sites
    url(r'^sites/$', 'sites.index', name="cciwmain.sites.index"),
    url(r'^sites/(?P<slug>.*)/$', 'sites.detail', name="cciwmain.sites.detail"),


) + patterns('cciw.forums.views',
    # News
    url(r'^news/$', 'news', name= 'cciwmain.site-news-index'),
    (r'^news/(?P<topicid>\d+)/$', 'topic', {'title_start': 'News'},
     'cciwmain.site-news-detail'),

    # Misc website stuff
    (r'^website/forum/$', 'topicindex', {'title': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add/$', 'add_topic', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add_news/$', 'add_news', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add_poll/$', 'edit_poll', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/edit_poll/(?P<poll_id>\d+)/$', 'edit_poll', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/(?P<topicid>\d+)/$', 'topic', {'title_start': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),

    url(r'^awards/$', 'award_index'),


    # Shortcuts
    (r'^posts/$', 'all_posts'),
    (r'^posts/(?P<id>\d+)/$', 'post'),
    (r'^topics/$', 'all_topics'),

) + patterns('cciw.cciwmain.views',

    # Services
    (r'^services/esv_passage/$', 'services.esv_passage'),

    # Feedback form
    url(r'^contact/$', 'misc.feedback', name="cciwmain.misc.feedback"),
    url(r'^contact/done/$', 'misc.feedback_done', name="cciwmain.misc.feedback_done"),

    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    (r'^(?:.*)/$|^$', 'htmlchunk.find'),
)

