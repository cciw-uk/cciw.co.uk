from django.conf.urls import patterns, url
from django.conf import settings

# Forums and news items are tightly integrated (read: tangled) into the main
# site, and always have been, so URLs and some view code for forums are part of
# the 'cciwmain' app rather than the 'forums' app.

urlpatterns = \
patterns('cciw.cciwmain.views',
    # Camps
    (r'^thisyear/$', 'camps.thisyear'),
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

    # Services
    (r'^services/esv_passage/$', 'services.esv_passage'),

    # ContactUs form
    url(r'^contact/$', 'misc.contact_us', name="cciwmain.misc.contact_us"),
    url(r'^contact/done/$', 'misc.contact_us_done', name="cciwmain.misc.contact_us_done"),

) + patterns('cciw.forums.views',

    # Members
    url(r'^login/$', 'members.login', name='cciwmain.members.login'),
    url(r'^members/$', 'members.index', name="cciwmain.members.index"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail', name="cciwmain.members.detail"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/posts/$', 'members.posts', name="cciwmain.members.posts"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/$', 'members.send_message', name="cciwmain.members.send_message"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/inbox/$', 'members.inbox', name="cciwmain.members.inbox"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/archived/$', 'members.archived_messages', name="cciwmain.members.archived_messages"),
    url(r'^signup/$', 'memberadmin.signup', name="cciwmain.memberadmin.signup"),
    url(r'^memberadmin/change-password/$', 'memberadmin.change_password', name='cciwmain.memberadmin.change_password'),
    url(r'^memberadmin/reset-password/(?P<uid>[0-9]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'memberadmin.reset_password', name="cciwmain.memberadmin.reset_password"),
    url(r'^memberadmin/change-email/$', 'memberadmin.change_email', name='cciwmain.memberadmin.change_email'),
    url(r'^memberadmin/preferences/$', 'memberadmin.preferences', name="cciwmain.memberadmin.preferences"),
    url(r'^help/logging-in/$', 'memberadmin.help_logging_in', name="cciwmain.memberadmin.help_logging_in"),

    # News
    url(r'^news/$', 'forums.news', name= 'cciwmain.site-news-index'),
    (r'^news/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'News'},
     'cciwmain.site-news-detail'),

    # Misc website stuff
    (r'^website/forum/$', 'forums.topicindex', {'title': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add/$', 'forums.add_topic', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add_news/$', 'forums.add_news', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add_poll/$', 'forums.edit_poll', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/edit_poll/(?P<poll_id>\d+)/$', 'forums.edit_poll', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),

    # Awards
    url(r'^awards/$', 'awards.index'),

    # Shortcuts
    (r'^posts/$', 'forums.all_posts'),
    (r'^posts/(?P<id>\d+)/$', 'forums.post'),
    (r'^topics/$', 'forums.all_topics'),

) + patterns('cciw.sitecontent.views',

    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    (r'^(?:.*)/$|^$', 'find'),
)

