from django.views.generic import list_detail
from django.core.exceptions import Http404
from django.models.forums import forums, topics
from cciw.apps.cciw.common import *
from django.utils.html import escape
from cciw.apps.cciw import utils

# Called directly as a view for /news/ and /website/forum/, and used by other views

def topicindex_breadcrumb(forum):
	return ["Topics"]

def photoindex_breadcrumb(gallery):
	return ["Photos"]

def topic_breadcrumb(forum, topic):
	return ['<a href="' + forum.get_absolute_url() + '">Topics</a>']

def photo_breadcrumb(gallery, photo):
	# TODO - add links for previous/next photo by ID
	return ['<a href="' + gallery.get_absolute_url() + '">Photos</a>', str(photo.id)]
	
def topicindex(request, title = None, extra_context = None, forum = None,
	template_name = 'forums/topicindex',	breadcrumb_extra = None, paginate_by = 15, default_order = ('-lastPostAt',)):
	"Displays an index of topics in a forum"
	if extra_context is None:
		if title is None:
			raise Exception("No title provided for page")
		extra_context = standard_extra_context(request, title = title)
		
	if forum is None:
		try:
			forum = forums.get_object(location__exact = request.path[1:])
		except forums.ForumDoesNotExist:
			raise Http404
	extra_context['forum'] = forum
	
	if breadcrumb_extra is None:
		breadcrumb_extra = []
	extra_context['breadcrumb'] =   create_breadcrumb(breadcrumb_extra + topicindex_breadcrumb(forum))

	# TODO - searching
	
	lookup_args = {
		'hidden__exact': False, # TODO - depends on permission
		'forum__id__exact': forum.id,
	} 
	
	order_option_to_lookup_arg(
		{'aca': ('createdAt', 'id'),
		'dca': ('-createdAt', '-id'),
		'apc': ('postCount',),
		'dpc': ('-postCount',),
		'alp': ('lastPostAt',),
		'dlp': ('-lastPostAt',)},
		lookup_args, request, default_order)
	extra_context['default_order'] = 'dlp' # corresonds = '-lastPostAt'
		
	return list_detail.object_list(request, 'forums', 'topics', 
		extra_context = extra_context, 
		template_name = template_name,
		paginate_by = paginate_by, extra_lookup_kwargs = lookup_args,
		allow_empty = True)

def topic(request, title_start = None, template_name = 'forums/topic', topicid = 0,
		introtext = None, breadcrumb_extra = None):
	"Displays a topic"
	if title_start is None:
		raise Exception("No title provided for page")
	
	try:
		# TODO - lookup depends on permissions
		topic = topics.get_object(id__exact = int(topicid))
	except topics.TopicDoesNotExist:
		raise Http404
			
	# Add additional title
	title = utils.get_extract(topic.subject, 30)
	if len(title_start) > 0:
		title = title_start + ": " + title
	
	
	extra_context = standard_extra_context(request, title = title)

	if breadcrumb_extra is None:
		breadcrumb_extra = []
	extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(topic.get_forum(), topic))
			
	extra_context['topic'] = topic
	if not topic.newsItem_id is None:
		extra_context['newsItem'] = topic.get_newsItem()
	if not topic.poll_id is None:
		extra_context['poll'] = topic.get_poll()
	if introtext:
		extra_context['introtext'] = introtext
	lookup_args = {
		'hidden__exact': False, # TODO - lookup depends on permissions
		'topic__id__exact': topic.id,
	} 
			
	return list_detail.object_list(request, 'forums', 'posts', 
		extra_context = extra_context, 
		template_name = template_name,
		paginate_by=25, extra_lookup_kwargs = lookup_args,
		allow_empty = True)

		
def photoindex(request, gallery, extra_context, breadcrumb_extra):
	"Displays an a gallery of photos"
	extra_context['gallery'] = gallery	
	extra_context['breadcrumb'] =   create_breadcrumb(breadcrumb_extra + photoindex_breadcrumb(gallery))

	lookup_args = {
		'hidden__exact': False, # TODO - lookup depends on permissions
		'gallery__id__exact': gallery.id,
	} 
	
	order_option_to_lookup_arg(
		{'aca': ('createdAt','id'),
		'dca': ('-createdAt','-id'),
		'apc': ('postCount',),
		'dpc': ('-postCount',),
		'alp': ('lastPostAt',),
		'dlp': ('-lastPostAt',)},
		lookup_args, request, ('createdAt', 'id'))
	extra_context['default_order'] = 'aca'
		
	return list_detail.object_list(request, 'forums', 'photos', 
		extra_context = extra_context, 
		template_name = 'forums/photoindex',
		paginate_by = 15, extra_lookup_kwargs = lookup_args,
		allow_empty = True)

def photo(request, photo, extra_context, breadcrumb_extra):
	"Displays a photo"
	extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + photo_breadcrumb(photo.get_gallery(), photo))
	extra_context['photo'] = photo
	lookup_args = {
		'hidden__exact': False, # TODO - lookup depends on permissions
		'photo__id__exact': photo.id,
	} 
			
	return list_detail.object_list(request, 'forums', 'posts', 
		extra_context = extra_context, 
		template_name = 'forums/photo',
		paginate_by=25, extra_lookup_kwargs = lookup_args,
		allow_empty = True)
