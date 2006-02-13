from django.conf.urls.defaults import *
import cciw.apps.cciw.common as cciw_common
from cciw.apps.cciw.models import Site, Award

urlpatterns = \
patterns('django.views.generic',
    (r'^awards/$', 'list_detail.object_list',
        {'queryset': Award.objects.order_by('-year', '-value'),
         'extra_context': cciw_common.standard_extra_context(title="Website Awards"),
         'template_name': 'cciw/awards/index',
         'allow_empty': True,
         }
    ),
         
    (r'^sites/$', 'list_detail.object_list',
        {'queryset': Site.objects.all(),
         'extra_context': cciw_common.standard_extra_context(title="Camp sites"),
         'template_name': 'cciw/sites/index'
        }
    ),
 
    (r'^sites/(?P<slug>.*)/$', 'list_detail.object_detail',
        {'queryset': Site.objects.all(),
         'slug_field': 'slug_name',
         'extra_context': cciw_common.standard_extra_context(),
         'template_name': 'cciw/sites/detail'
         }
        
    ),
    
) + \
patterns('cciw.apps.cciw.views',
    (r'^login/$', 'members.login'),
    (r'^members/$', 'members.index'),
    (r'^members/(?P<user_name>[A-Za-z0-9_]+)/$', 'members.detail'),
    (r'^thisyear/$', 'camps.thisyear'),
    
    (r'^camps/$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/?$', 'camps.index'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', 'camps.detail'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/$', 'camps.forum'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+|all)/forum/(?P<topicnumber>\d+)/$', 'camps.topic'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/$', 'camps.gallery'),
    (r'^camps/(?P<year>\d{4})/(?P<number>\d+)/photos/(?P<photonumber>\d+)/$', 'camps.photo'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/$', 'camps.oldcampgallery'),
    (r'^camps/(?P<year>.*)/(?P<galleryname>.*)/photos/(?P<photonumber>\d+)/$', 'camps.oldcampphoto'),
    
    (r'^news/$', 'forums.topicindex', 
        {'title': 'News', 
        'template_name': 'cciw/forums/newsindex', 
        'paginate_by' : 6,
        'default_order': ('-created_at',)}), 
    (r'^news/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'News'}), # TODO - create different template ?
    (r'^website/forum/$', 'forums.topicindex', {'title': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    (r'^website/forum/(?P<topicid>\d+)/$', 'forums.topic', {'title_start': 'Website forum',
        'breadcrumb_extra': ['<a href="/website/">About website</a>']}),
    
    (r'', 'htmlchunk.find'),
) 

