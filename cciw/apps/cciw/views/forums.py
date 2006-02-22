import datetime
from django.views.generic import list_detail
from django.http import Http404
from cciw.apps.cciw.models import Forum, Topic, Photo, Post
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
    prev_and_next = ''
    try:
        previous_photo = Photo.objects.filter(id__lt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('-id')[0]
        prev_and_next += '<a href="%s" title="Previous photo">&laquo;</a> ' % previous_photo.get_absolute_url() 
    except Photo.DoesNotExist:
        prev_and_next += '&laquo; '
        
    try:
        next_photo = Photo.objects.filter(id__gt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('id')[0]
        prev_and_next += '<a href="%s" title="Next photo">&raquo;</a> ' % next_photo.get_absolute_url()
    except Photo.DoesNotExist:
        prev_and_next += '&raquo; '
        
    return ['<a href="' + gallery.get_absolute_url() + '">Photos</a>', str(photo.id), prev_and_next]
    
def topicindex(request, title=None, extra_context=None, forum=None,
    template_name='cciw/forums/topicindex', breadcrumb_extra=None, paginate_by=15, default_order=('-last_post_at',)):
    "Displays an index of topics in a forum"
    if extra_context is None:
        if title is None:
            raise Exception("No title provided for page")
        extra_context = standard_extra_context(title=title)
        
    if forum is None:
        try:
            forum = Forum.objects.get(location=request.path[1:])
        except Forum.DoesNotExist:
            raise Http404
    extra_context['forum'] = forum
    
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topicindex_breadcrumb(forum))

    # TODO - searching
    
    lookup_args = {
        'hidden': False, # TODO - depends on permission
        'forum__id__exact': forum.id,
    } 
    
    order_by = get_order_option(
        {'aca': ('created_at', 'id'),
        'dca': ('-created_at', '-id'),
        'apc': ('post_count',),
        'dpc': ('-post_count',),
        'alp': ('last_post_at',),
        'dlp': ('-last_post_at',),
        },
        request, default_order)
    extra_context['default_order'] = 'dlp' # corresponds = '-last_post_at'
        
    return list_detail.object_list(request, Topic.objects.filter(**lookup_args).order_by(*order_by),
        extra_context=extra_context, template_name=template_name,
        paginate_by=paginate_by, allow_empty=True)

def topic(request, title_start=None, template_name='cciw/forums/topic', topicid=0,
        introtext=None, breadcrumb_extra=None):
    """Displays a topic"""
    if title_start is None:
        raise Exception("No title provided for page")
    
    try:
        # TODO - lookup depends on permissions
        topic = Topic.objects.get(id=int(topicid))
    except Topic.DoesNotExist:
        raise Http404
            
    # Add additional title
    title = utils.get_extract(topic.subject, 30)
    if len(title_start) > 0:
        title = title_start + ": " + title

    extra_context = standard_extra_context(title=title)

    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(topic.forum, topic))
            
    extra_context['topic'] = topic
    if not topic.news_item_id is None:
        extra_context['news_item'] = topic.news_item
        
    if not topic.poll_id is None:
        poll = topic.poll
        extra_context['poll'] = poll
        if poll.voting_ends < datetime.datetime.now(): # or they just voted, or can no longer vote
            extra_context['show_poll_results'] = True
        # TODO handle voting on polls
        
        
    if introtext:
        extra_context['introtext'] = introtext
    lookup_args = {
        'hidden': False, # TODO - lookup depends on permissions
        'topic__id__exact': topic.id,
    } 
            
    return list_detail.object_list(request, Post.objects.filter(**lookup_args), 
        extra_context=extra_context, template_name=template_name,
        paginate_by=15, allow_empty=True)

def photoindex(request, gallery, extra_context, breadcrumb_extra):
    "Displays an a gallery of photos"
    extra_context['gallery'] = gallery    
    extra_context['breadcrumb'] =   create_breadcrumb(breadcrumb_extra + photoindex_breadcrumb(gallery))

    lookup_args = {
        'hidden': False, # TODO - lookup depends on permissions
        'gallery__id__exact': gallery.id,
    } 
    
    order_by = get_order_option(
        {'aca': ('created_at','id'),
        'dca': ('-created_at','-id'),
        'apc': ('post_count',),
        'dpc': ('-post_count',),
        'alp': ('last_post_at',),
        'dlp': ('-last_post_at',)},
        request, ('created_at', 'id'))
    extra_context['default_order'] = 'aca'

    return list_detail.object_list(request, Photo.objects.filter(**lookup_args).order_by(*order_by), 
        extra_context=extra_context, template_name='cciw/forums/photoindex',
        paginate_by=15, allow_empty=True)

def photo(request, photo, extra_context, breadcrumb_extra):
    "Displays a photo"
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + photo_breadcrumb(photo.gallery, photo))
    extra_context['photo'] = photo
    
    lookup_args = {
        'hidden': False, # TODO - lookup depends on permissions
        'photo__id__exact': photo.id,
    } 
    
    return list_detail.object_list(request, Post.objects.filter(**lookup_args),
        extra_context=extra_context, template_name='cciw/forums/photo',
        paginate_by=25, allow_empty=True)
