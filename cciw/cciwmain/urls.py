from django.conf.urls import url
from django.conf import settings
from django.utils.html import mark_safe

from cciw.cciwmain.views import camps as camp_views
from cciw.cciwmain.views import sites as sites_views
from cciw.cciwmain.views import services as services_views
from cciw.cciwmain.views import misc as misc_views
from cciw.forums.views import awards as awards_views
from cciw.forums.views import members as members_views
from cciw.forums.views import memberadmin as memberadmin_views
from cciw.forums.views import forums as forums_views
from cciw.sitecontent import views as sitecontent_views


# Forums and news items are tightly integrated (read: tangled) into the main
# site, and always have been, so URLs and some view code for forums are part of
# the 'cciwmain' app rather than the 'forums' app.


# TODO - URLs have inconsistent names, should clean up


about_website_link = mark_safe('<a href="/website/">About website</a>')

urlpatterns = [
    # Camps
    url(r'^thisyear/$', camp_views.thisyear, name="cciw-cciwmain-thisyear"),
    url(r'^camps/$', camp_views.index, name="cciw-cciwmain-index"),
    url(r'^camps/(?P<year>\d{4})/?$', camp_views.index, name="cciw-cciwmain-index"),
    url(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', camp_views.detail, name="cciw-cciwmain-detail"),
    url(r'^' + settings.CAMP_FORUM_RE + r'$', camp_views.forum, name="cciw-cciwmain-camp_forum"),
    url(r'^' + settings.CAMP_FORUM_RE + r'(?P<topicnumber>\d+)/$', camp_views.topic, name='cciw-cciwmain-camp_topic'),
    url(r'^' + settings.CAMP_FORUM_RE + r'add/$', camp_views.add_topic, name="cciw-cciwmain-camp_add_topic"),
    url(r'^' + settings.CAMP_FORUM_RE + r'add_news/$', camp_views.add_news, name="cciw-cciwmain-camp_add_news"),
    url(r'^' + settings.CAMP_FORUM_RE + r'add_poll/$', camp_views.edit_poll, name='cciw-cciwmain-camp_add_poll'),
    url(r'^' + settings.CAMP_FORUM_RE + r'edit_poll/(?P<poll_id>\d+)/$', camp_views.edit_poll, name='cciw-cciwmain-camp_edit_poll'),

    url(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', camp_views.gallery, name="cciw-cciwmain-camp_gallery"),
    url(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', camp_views.photo, name="cciw-cciwmain-camp_photo"),
    url(r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', camp_views.oldcampgallery, name="cciw-cciwmain-camp_oldgallery"),
    url(r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', camp_views.oldcampphoto, name="cciw-cciwmain-camp_oldphoto"),

    # Sites
    url(r'^sites/$', sites_views.index, name="cciw-cciwmain-sites_index"),
    url(r'^sites/(?P<slug>.*)/$', sites_views.detail, name="cciw-cciwmain-sites_detail"),

    # Services
    url(r'^services/esv_passage/$', services_views.esv_passage, name="cciw-cciwmain-services_esv_passage"),

    # ContactUs form
    url(r'^contact/$', misc_views.contact_us, name="cciw-cciwmain-contact_us"),
    url(r'^contact/done/$', misc_views.contact_us_done, name="cciw-cciwmain-contact_us_done"),

    # Members
    url(r'^login/$', members_views.login, name='cciw-cciwmain-members_login'),
    url(r'^members/$', members_views.index, name="cciw-cciwmain-members_index"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', members_views.detail, name="cciw-cciwmain-members_detail"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/posts/$', members_views.posts, name="cciw-cciwmain-members_posts"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/$', members_views.send_message, name="cciw-cciwmain-members_send_message"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/inbox/$', members_views.inbox, name="cciw-cciwmain-members_inbox"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/archived/$', members_views.archived_messages, name="cciw-cciwmain-members_archived_messages"),
    url(r'^signup/$', memberadmin_views.signup, name="cciw-cciwmain-members_signup"),
    url(r'^memberadmin/change-password/$', memberadmin_views.change_password, name='cciw-cciwmain-members_change_password'),
    url(r'^memberadmin/reset-password/(?P<uid>[0-9]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        memberadmin_views.reset_password, name="cciw-cciwmain-members_reset_password"),
    url(r'^memberadmin/change-email/$', memberadmin_views.change_email, name='cciw-cciwmain-members_change_email'),
    url(r'^memberadmin/preferences/$', memberadmin_views.preferences, name="cciw-cciwmain-members_preferences"),
    url(r'^help/logging-in/$', memberadmin_views.help_logging_in, name="cciw-cciwmain-members_help_logging_in"),

    # News
    url(r'^news/$', forums_views.news, name='cciw-cciwmain-site_news_index'),
    url(r'^news/(?P<topicid>\d+)/$', forums_views.topic,
        {'title_start': 'News'},
        name='cciw-cciwmain-site_news_detail'),

    # Misc website stuff
    url(r'^website/forum/$', forums_views.topicindex,
        {'title': 'Website forum', 'breadcrumb_extra': [about_website_link]}),
    url(r'^website/forum/add/$', forums_views.add_topic, {'breadcrumb_extra': [about_website_link]}),
    url(r'^website/forum/add_news/$', forums_views.add_news, {'breadcrumb_extra': [about_website_link]}),
    url(r'^website/forum/add_poll/$', forums_views.edit_poll, {'breadcrumb_extra': [about_website_link]}),
    url(r'^website/forum/edit_poll/(?P<poll_id>\d+)/$', forums_views.edit_poll,
        {'breadcrumb_extra': [about_website_link]}),
    url(r'^website/forum/(?P<topicid>\d+)/$', forums_views.topic,
        {'title_start': 'Website forum', 'breadcrumb_extra': [about_website_link]}),

    # Awards
    url(r'^awards/$', awards_views.index, name="cciw-cciwmain-awards_index"),

    # Shortcuts
    url(r'^posts/$', forums_views.all_posts, name="cciw-cciwmain-forums_all_posts"),
    url(r'^posts/(?P<id>\d+)/$', forums_views.post, name="cciw-cciwmain-forums_post"),
    url(r'^topics/$', forums_views.all_topics, name="cciw-cciwmain-forums_all_topics"),

    # Site content
    url(r'^$', sitecontent_views.home, name="cciw-cciwmain-sitecontent_home"),
    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    url(r'^(?:.*)/$|^$', sitecontent_views.find, name="cciw-cciwmain-sitecontent_find"),
]
