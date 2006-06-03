from django.conf.urls.defaults import patterns
import cciw.cciwmain.common as cciw_common
from cciw.cciwmain.models import Site, Award
from django.conf import settings

urlpatterns = \
patterns('django.views.generic',
    (r'^awards/$', 'list_detail.object_list',
        {'queryset': Award.objects.order_by('-year', '-value'),
         'extra_context': cciw_common.standard_extra_context(title="Website Awards"),
         'template_name': 'cciw/awards/index.html',
         'allow_empty': True,
         }
    ),

    (r'^sites/$', 'list_detail.object_list',
        {'queryset': Site.objects.all(),
         'extra_context': cciw_common.standard_extra_context(title="Camp sites"),
         'template_name': 'cciw/sites/index.html'
        }
    ),
 
    (r'^sites/(?P<slug>.*)/$', 'list_detail.object_detail',
        {'queryset': Site.objects.all(),
         'slug_field': 'slug_name',
         'extra_context': cciw_common.standard_extra_context(),
         'template_name': 'cciw/sites/detail.html'
         }
        
    ),
    
) + \
patterns('cciw.cciwmain.views',
    # Members
    (r'^login/$', 'members.login'),
    (r'^members/$', 'members.index'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/posts/$', 'members.posts'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/$', 'members.send_message'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/inbox/$', 'members.inbox'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/messages/archived/$', 'members.archived_messages'),
    (r'^signup/$', 'memberadmin.signup'),
    (r'^memberadmin/change-password/$', 'memberadmin.change_password'),
    (r'^memberadmin/change-email/$', 'memberadmin.change_email'),
    (r'^memberadmin/preferences/$', 'memberadmin.preferences'),
    (r'^help/logging-in/$', 'memberadmin.help_logging_in'),
    
    # Camps
    (r'^thisyear/$', 'camps.thisyear'),
    (r'^camps/$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', 'camps.detail'),
    (r'^' + settings.CAMP_FORUM_RE + r'$', 'camps.forum'),
    (r'^' + settings.CAMP_FORUM_RE + r'(?P<topicnumber>\d+)/$', 'camps.topic'),
    (r'^' + settings.CAMP_FORUM_RE + r'add/$', 'camps.add_topic'),
    (r'^' + settings.CAMP_FORUM_RE + r'add_news/$', 'camps.add_news'),
    (r'^' + settings.CAMP_FORUM_RE + r'add_poll/$', 'camps.edit_poll'),
    (r'^' + settings.CAMP_FORUM_RE + r'edit_poll/(?P<poll_id>\d+)/$', 'camps.edit_poll'),
    
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', 'camps.gallery'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', 'camps.photo'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', 'camps.oldcampgallery'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', 'camps.oldcampphoto'),
    
    # News
    (r'^news/$', 'forums.topicindex', 
        {'title': 'News', 
        'template_name': 'cciw/forums/newsindex.html', 
        'paginate_by' : 6,
        'default_order': ('-created_at',)}), 
    (r'^news/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'News'}),

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
    (r'services/esv_passage/$', 'services.esv_passage'),
    
    (r'', 'htmlchunk.find'),
) 

