from django.conf.urls.defaults import patterns, url
import cciw.cciwmain.common as cciw_common
from cciw.cciwmain.common import DefaultMetaData
from cciw.cciwmain.utils import UseOnceLazyDict
from cciw.cciwmain.models import Site, Award
from django.conf import settings
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

class AwardList(DefaultMetaData, ListView):
    metadata_title = "Website Awards"
    template_name = "cciw/awards/index.html"
    queryset = Award.objects.order_by('-year', '-value')

class SiteList(DefaultMetaData, ListView):
    metadata_title = "Camp sites"
    template_name='cciw/sites/index.html'
    queryset = Site.objects.all()

class SiteDetail(DefaultMetaData, DetailView):
    queryset = Site.objects.all()
    slug_field = 'slug_name'
    template_name = 'cciw/sites/detail.html'

urlpatterns = \
patterns('',
         url(r'^awards/$', AwardList.as_view(), name="cciwmain.awards.index"),
         url(r'^sites/$', SiteList.as_view(), name="cciwmain.sites.index"),
         url(r'^sites/(?P<slug>.*)/$', SiteDetail.as_view(), name="cciwmain.sites.detail"),
) + \
patterns('cciw.cciwmain.views',
    # Members
    (r'^login/$', 'members.login'),
    url(r'^members/$', 'members.index', name="cciwmain.members.index"),
    url(r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail', name="cciwmain.members.detail"),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/posts/$', 'members.posts'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/$', 'members.send_message'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/inbox/$', 'members.inbox'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/archived/$', 'members.archived_messages'),
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

    # News
    (r'^news/$', 'forums.topicindex',
        {'title': 'News',
        'template_name': 'cciw/forums/newsindex.html',
        'paginate_by' : 6,
        'default_order': ('-created_at',)},
     'cciwmain.site-news-index'),
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

    # Shortcuts
    (r'^posts/$', 'forums.all_posts'),
    (r'^posts/(?P<id>\d+)/$', 'forums.post'),
    (r'^topics/$', 'forums.all_topics'),

    # Tagging
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/tags/$', 'tagging.members_tags'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/tags/(?P<text>[^/]*)/$', 'tagging.members_tags_single_text'),
    (r'^edit_tag/(?P<model_name>[A-Za-z0-9_]+)/(?P<object_id>[^/]*)/$', 'tagging.edit_tag'),
    (r'^tags/$', 'tagging.index'),
    (r'^tags/(?P<text>[^/]*)/$', 'tagging.recent_and_popular_targets'),
    (r'^tag_targets/(?P<model_name>[A-Za-z0-9_]+)/(?P<object_id>[^/]*)/$', 'tagging.tag_target'),
    (r'^tag_targets/(?P<model_name>[A-Za-z0-9_]+)/(?P<object_id>[^/]*)/(?P<text>[^/]*)/$', 'tagging.tag_target_single_text'),
    (r'^tag_targets/(?P<model_name>[A-Za-z0-9_]+)/(?P<object_id>[^/]*)/(?P<text>[^/]*)/(?P<tag_id>[^/]*)/$', 'tagging.single_tag'),
    (r'^tag_search/$', 'tagging.search'),


    # Services
    (r'^services/esv_passage/$', 'services.esv_passage'),

    # Feedback form
    url(r'^contact/$', 'misc.feedback', name="cciwmain.misc.feedback"),

    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    (r'^(?:.*)/$|^$', 'htmlchunk.find'),
)

