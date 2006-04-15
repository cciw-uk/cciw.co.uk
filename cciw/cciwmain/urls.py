from django.conf.urls.defaults import patterns
import cciw.cciwmain.common as cciw_common
from cciw.cciwmain.models import Site, Award

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
    (r'^login/$', 'members.login'),
    (r'^members/$', 'members.index'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail'),
    ('^members/(?P<user_name>.*)/messages/$', 'members.send_message'),
    ('^members/(?P<user_name>.*)/messages/inbox/$', 'members.inbox'),
    ('^members/(?P<user_name>.*)/messages/archived/$', 'members.archived_messages'),
    (r'^thisyear/$', 'camps.thisyear'),
    
    (r'^camps/$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', 'camps.detail'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/$', 'camps.forum'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/(?P<topicnumber>\d+)/$', 'camps.topic'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/add/$', 'camps.add_topic'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/add_news/$', 'camps.add_news'),
    
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', 'camps.gallery'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', 'camps.photo'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', 'camps.oldcampgallery'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', 'camps.oldcampphoto'),
    
    (r'^news/$', 'forums.topicindex', 
        {'title': 'News', 
        'template_name': 'cciw/forums/newsindex.html', 
        'paginate_by' : 6,
        'default_order': ('-created_at',)}), 
    (r'^news/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'News'}),

    (r'^website/forum/$', 'forums.topicindex', {'title': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add/$', 'forums.add_topic', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/add_news/$', 'forums.add_news', {'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
        
    (r'^posts/$', 'forums.posts'),
    (r'^posts/(?P<id>\d+)/$', 'forums.post'),
    
    (r'', 'htmlchunk.find'),
) 

