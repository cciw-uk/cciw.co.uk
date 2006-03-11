import datetime
from django.views.generic import list_detail
from django.http import Http404, HttpResponseForbidden
from cciw.cciwmain.models import Forum, Topic, Photo, Post, Member
from cciw.cciwmain.common import get_current_member, create_breadcrumb, standard_extra_context, get_order_option
from cciw.cciwmain.decorators import login_redirect
from django.utils.html import escape
from cciw.cciwmain import utils
from cciw.cciwmain.templatetags import bbcode
from datetime import datetime

# Utility functions for breadcrumbs
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
    
# Called directly as a view for /news/ and /website/forum/, and used by other views
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

# Used as part of a view function
def process_post(request, topic, photo, context):
    """Processes a posted message for a photo or a topic.
    One of 'photo' or 'topic' should be set."""

    cur_member = get_current_member(request)
    if cur_member is None:
        # silently failing is OK, should never get here
        return  
      
    if not request.POST.has_key('post') and \
       not request.POST.has_key('preview'):
        return # they didn't try to post
      
    errors = []
    if (topic and not topic.open) or \
        (photo and not photo.open):
        # Only get here if the topic was closed 
        # while they were adding a message
        errors.append('This thread is closed, sorry.')
        # For this error, there is nothing more to say so return immediately
        context['errors'] = errors
        return None
    
    msg_text = request.POST.get('message', '').strip()
    if msg_text == '':
        errors.append('You must enter a message.')
    
    context['errors'] = errors
    
    # Preview
    if request.POST.has_key('preview'):
        context['message_text'] = bbcode.correct(msg_text)
        if not errors:
            context['preview'] = bbcode.bb2xhtml(msg_text)

    # Post        
    if not errors and request.POST.has_key('post'):
        post = Post(posted_by=cur_member, 
                  subject='',
                  message=msg_text,
                  hidden=(cur_member.moderated == Member.MODERATE_ALL),
                  needs_approval=(cur_member.moderated == Member.MODERATE_ALL),
                  topic=topic,
                  photo=photo,
                  posted_at=datetime.now())
        post.save()
        # TODO - do a redirect to the page, and to the
        # exact post that was added.  To work correctly,
        # it will have to take paging into account i.e. this
        # post might be on a new page

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

    # Process any message that they added.
    process_post(request, topic, None, extra_context)
    
    # TODO - process moderator stuff
 
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(topic.forum, topic))
            
    extra_context['topic'] = topic
    if not topic.news_item_id is None:
        extra_context['news_item'] = topic.news_item
    
    if not topic.poll_id is None:
        poll = topic.poll
        extra_context['poll'] = poll
        if poll.voting_ends < datetime.datetime.now(): # TODO or they just voted, or can no longer vote
            extra_context['show_poll_results'] = True
        # TODO handle voting on polls
                
    if introtext:
        extra_context['introtext'] = introtext

    lookup_args = {
        'hidden': False, # TODO - lookup depends on permissions
        'topic__id__exact': topic.id,
    }
    
    if topic.open:
        if get_current_member(request) is not None:
            extra_context['show_message_form'] = True
        else:
            extra_context['login_link'] = login_redirect(request.get_full_path() + '#messageform')

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
