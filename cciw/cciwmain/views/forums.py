from datetime import datetime, date
import string

from django.views.generic import list_detail
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings
from django import forms
from django.forms import widgets
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe

from cciw.cciwmain.models import Forum, Topic, Photo, Post, Member, VoteInfo, NewsItem, Permission, Poll, PollOption
from cciw.cciwmain.common import create_breadcrumb, standard_extra_context, get_order_option, object_list
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain.decorators import login_redirect
from django.utils.html import escape
from cciw.cciwmain import utils
from cciw.cciwmain.templatetags import bbcode
from cciw.cciwmain.decorators import member_required, member_required_for_post
from cciw.cciwmain import feeds
from cciw.cciwmain import forms as cciwforms


# Utility functions for breadcrumbs
def topicindex_breadcrumb(forum):
    return [u"Topics"]

def photoindex_breadcrumb(gallery):
    return [u"Photos"]

def topic_breadcrumb(forum, topic):
    return [u'<a href="%s">Topics</a>' % forum.get_absolute_url()]

def photo_breadcrumb(gallery, photo):
    prev_and_next = u''
    try:
        previous_photo = Photo.objects.filter(id__lt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('-id')[0]
        prev_and_next += u'<a href="%s" title="Previous photo">&laquo;</a> ' % previous_photo.get_absolute_url()
    except IndexError:
        prev_and_next += u'&laquo; '

    try:
        next_photo = Photo.objects.filter(id__gt=photo.id, \
            gallery__id__exact = photo.gallery_id).order_by('id')[0]
        prev_and_next += u'<a href="%s" title="Next photo">&raquo;</a> ' % next_photo.get_absolute_url()
    except IndexError:
        prev_and_next += u'&raquo; '

    return [u'<a href="%s">Photos</a>' % gallery.get_absolute_url(), unicode(photo.id), prev_and_next]

# Called directly as a view for /news/ and /website/forum/, and used by other views
def topicindex(request, title=None, extra_context=None, forum=None,
    template_name='cciw/forums/topicindex.html', breadcrumb_extra=None,
    paginate_by=settings.FORUM_PAGINATE_TOPICS_BY, default_order=('-last_post_at',)):
    "Displays an index of topics in a forum"

    ### FORUM ###
    forum = _get_forum_or_404(request.path, '')

    ### TOPICS ###
    topics = forum.topics.all().select_related('forum')

    ### FEED ###
    resp = feeds.handle_feed_request(request, feeds.forum_topic_feed(forum), query_set=topics)
    if resp: return resp

    if extra_context is None:
        if title is None:
            raise Exception("No title provided for page")
        extra_context = standard_extra_context(title=title)

    extra_context['forum'] = forum
    extra_context['atom_feed_title'] = u"Atom feed for new topics on this board."

    ### BREADCRUMB ###
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topicindex_breadcrumb(forum))

    ### ORDERING ###
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
    topics = topics.order_by(*order_by)

    ### PERMISSIONS ###
    if request.user.has_perm('cciwmain.edit_topic'):
        extra_context['moderator'] = True

    return object_list(request, topics, extra_context=extra_context,
                       template_name=template_name, paginate_by=paginate_by)

def _get_forum_or_404(path, suffix):
    """Returns a forum from the supplied path (minus the suffix)
    or throws a 404 if it can't be found."""
    if suffix:
        location = path[1:-len(suffix)] # strip 'add/' or 'add_news/' bit
    else:
        location = path[1:]
    try:
        return Forum.objects.get(location=location)
    except Forum.DoesNotExist:
        raise Http404


# Called directly as a view for /website/forum/, and used by other views
@member_required
def add_topic(request, breadcrumb_extra=None):
    """
    Displays a page for adding a topic to a forum
    """

    forum = _get_forum_or_404(request.path, 'add/')

    cur_member = get_current_member()
    context = RequestContext(request, standard_extra_context(title='Add topic'))

    if not forum.open:
        context['message'] = u'This forum is closed - new topics cannot be added.'
    else:
        context['forum'] = forum
        context['show_form'] = True

    errors = []
    # PROCESS POST
    if forum.open and request.POST.has_key('post') or request.POST.has_key('preview'):
        subject = request.POST.get('subject', '').strip()
        msg_text = request.POST.get('message', '').strip()

        if subject == '':
            errors.append(u'You must enter a subject')

        if msg_text == '':
            errors.append(u'You must enter a message.')

        context['message_text'] = bbcode.correct(msg_text)
        context['subject_text'] = subject
        if not errors:
            if request.POST.has_key('post'):
                topic = Topic.create_topic(cur_member, subject, forum)
                topic.save()
                post = Post.create_post(cur_member, msg_text, topic, None)
                post.save()
                return HttpResponseRedirect('../%s/' % topic.id)
            else:
                context['preview'] = mark_safe(bbcode.bb2xhtml(msg_text))

    context['errors'] = errors
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(forum, None))
    return render_to_response('cciw/forums/add_topic.html', context_instance=context)

# Called directly as a view for /website/forum/, and used by other views
@member_required
def add_news(request, breadcrumb_extra=None):
    """
    Displays a page for adding a short news item to a forum.
    """

    forum = _get_forum_or_404(request.path, 'add_news/')

    cur_member = get_current_member()
    if not cur_member.has_perm(Permission.NEWS_CREATOR):
        return HttpResponseForbidden("Permission denied")

    context = RequestContext(request, standard_extra_context(title='Add short news item'))

    if not forum.open:
        context['message'] = 'This forum is closed - new news items cannot be added.'
    else:
        context['forum'] = forum
        context['show_form'] = True

    errors = []
    # PROCESS POST
    if forum.open and request.POST.has_key('post') or request.POST.has_key('preview'):
        subject = request.POST.get('subject', '').strip()
        msg_text = request.POST.get('message', '').strip()

        if subject == u'':
            errors.append(u'You must enter a subject.')

        if msg_text == u'':
            errors.append(u'You must enter the short news item.')

        context['message_text'] = bbcode.correct(msg_text)
        context['subject_text'] = subject
        if not errors:
            if request.POST.has_key('post'):
                newsitem = NewsItem.create_item(cur_member, subject, msg_text)
                newsitem.save()
                topic = Topic.create_topic(cur_member, subject, forum)
                topic.news_item_id = newsitem.id
                topic.save()
                return HttpResponseRedirect('../%s/' % topic.id)
            else:
                context['preview'] = mark_safe(bbcode.bb2xhtml(msg_text))

    context['errors'] = errors
    if breadcrumb_extra is None:
        breadcrumb_extra = []
    context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(forum, None))
    return render_to_response('cciw/forums/add_news.html', context_instance=context)

def update_poll_options(poll, new_option_list):
    """Takes a Poll object and a list of strings,
    and updates the PollOptions related to the Poll."""
    existing_options = list(poll.poll_options.order_by('listorder'))

    # This assumes order has not been messed with (as the user was instructed)

    if len(new_option_list) == len(existing_options):
        # indicates changes to the text only
        for existing_opt, new_text in zip(existing_options, new_option_list):
            existing_opt.text = new_text
            existing_opt.save()
    elif len(new_option_list) > len(existing_options):
        # Addition
        new_list = []
        ex_option, new_option_t = None, None

        while len(new_option_list) > 0:
            if len(existing_options) > 0:
                ex_option = existing_options[-1]
            else:
                ex_option = None

            new_option_t = new_option_list[-1]

            if ex_option is not None and ex_option.text == new_option_t:
                # Same as before
                new_list.insert(0, existing_options.pop())
                # throw away what we've dealt with
                new_option_list.pop()
            else: # ex_option is None or the text values are different
                # This is an addition
                text = new_option_list.pop()
                new_option = PollOption(text=text, poll=poll, total=0)
                new_list.insert(0, new_option)

        for i, po in enumerate(new_list):
            po.listorder = i
            po.save()

    elif len(existing_options) > len(new_option_list):
         # Removal
        new_list = []
        ex_option, new_option_t = None, None

        while len(existing_options) > 0:
            ex_option = existing_options[-1]

            if len(new_option_list) > 0:
                new_option_t = new_option_list[-1]
            else:
                new_option_t = None

            if new_option_t is not None and ex_option.text == new_option_t:
                # Same as before
                new_list.insert(0, existing_options.pop())
                # throw away what we've dealt with
                new_option_list.pop()
            else: # new_option_t is None or the text values are different
                # This is a removal
                old_option = existing_options.pop()
                old_option.delete()

        for i, po in enumerate(new_list):
            po.listorder = i
            po.save()

class PollOptionListField(forms.CharField):
    widget = widgets.Textarea
    def clean(self, value):
        """Parses a string containing multiple lines of text,
        and returns a list of poll options or raises ValidationError"""
        value = super(PollOptionListField, self).clean(value)
        l = filter(lambda opt: len(opt) > 0, map(string.strip, value.split("\n")))

        if len(l) == 0:
            raise forms.ValidationError(u"At least one option must be entered")

        max_length = PollOption._meta.get_field('text').max_length
        if len(filter(lambda opt: len(opt) > max_length, l)) > 0:
            raise forms.ValidationError(u"Options may not be more than %s chars long" % max_length)

        return l

class CreatePollForm(cciwforms.CciwFormMixin, forms.ModelForm):
    voting_starts = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget,
                                             label="Voting starts")
    voting_ends = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget,
                                           label="Voting ends")
    polloptions = PollOptionListField(label='Options (one per line)')

    class Meta:
        model = Poll
        fields = ['title', 'intro_text', 'outro_text', 'voting_starts', 'voting_ends', 'rules', 'rule_parameter']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        initial = kwargs.pop('initial', {})
        if instance is not None:
            initial['polloptions'] = '\n'.join(po.text for po in instance.poll_options.order_by('listorder'))
        kwargs['initial'] = initial
        super(CreatePollForm, self).__init__(*args, **kwargs)

# Overriding CreatePollForm to get the fields in the right order
# is currently rather tricky.  Easiest hack is this:
CreatePollForm.base_fields.keyOrder = ['title', 'intro_text', 'polloptions', 'outro_text', 'voting_starts', 'voting_ends', 'rules', 'rule_parameter']

@member_required
def edit_poll(request, poll_id=None, breadcrumb_extra=None):
    if poll_id is None:
        suffix = 'add_poll/'
        title = u"Create poll"
        existing_poll = None
    else:
        suffix = '/'.join(request.path.split('/')[-3:]) # 'edit_poll/xx/'
        title = u"Edit poll"
        existing_poll = get_object_or_404(Poll.objects.filter(id=poll_id))

    cur_member = get_current_member()
    if not cur_member.has_perm(Permission.POLL_CREATOR):
        return HttpResponseForbidden("Permission denied")
    if existing_poll and existing_poll.created_by != cur_member:
        return HttpResponseForbidden("Access denied.")

    forum = _get_forum_or_404(request.path, suffix)
    c = standard_extra_context(title=title)

    if request.method == 'POST':
        form = CreatePollForm(request.POST, instance=existing_poll)

        json = utils.json_validation_request(request, form)
        if json: return json

        if form.is_valid():
            new_poll = form.save(commit=False)
            new_poll.created_by_id = cur_member.user_name
            new_poll.save()

            if existing_poll is None:
                # new poll, create a topic to go with it
                topic = Topic.create_topic(cur_member, new_poll.title, forum)
                topic.poll_id = new_poll.id
                topic.save()
            else:
                # It will already have a topic associated
                topic = new_poll.topics.all()[0]
                topic.subject = new_poll.title
                topic.save()

            update_poll_options(new_poll, form.cleaned_data['polloptions'])

            return HttpResponseRedirect(topic.get_absolute_url())
    else:
        if existing_poll:
            form = CreatePollForm(instance=existing_poll)
        else:
            today = datetime.today()
            today = datetime(today.year, today.month, today.day)
            form = CreatePollForm(initial=dict(voting_starts=today))

    c['form'] = form
    c['existing_poll'] = existing_poll
    return render_to_response('cciw/forums/edit_poll.html',
                              context_instance=RequestContext(request, c))


# Used as part of a view function
def process_post(request, topic, photo, context):
    """Processes a posted message for a photo or a topic.
    One of 'photo' or 'topic' should be set.
    context is the context dictionary of the page, to which
    'errors' or 'message' might be added."""

    cur_member = get_current_member()
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
            context['preview'] = mark_safe(bbcode.bb2xhtml(msg_text))

    # Post
    if not errors and request.POST.has_key('post'):
        post = Post.create_post(cur_member, msg_text, topic, photo)
        post.save()
        return HttpResponseRedirect(post.get_forum_url())

def process_vote(request, topic, context):
    """Processes any votes posted on the topic.
    topic is the topic that might have a poll.
    context is the context dictionary of the page, to which
    voting_errors or voting_message might be added."""

    if topic.poll_id is None:
        # No poll
        return

    poll = topic.poll

    cur_member = get_current_member()
    if cur_member is None:
        # silently failing is OK, should never get here
        return

    try:
        polloption_id = int(request.POST['polloption'])
    except (ValueError, KeyError):
        return # they didn't try to vote, or invalid input

    errors = []
    if not poll.can_anyone_vote():
        # Only get here if the poll was closed
        # while they were voting
        errors.append(u'This poll is closed for voting, sorry.')
        context['voting_errors'] = errors
        return

    if not poll.can_vote(cur_member):
        errors.append(u'You cannot vote on this poll.  Please check the voting rules.')
        context['voting_errors'] = errors

    if not polloption_id in (po.id for po in poll.poll_options.all()):
        errors.append(u'Invalid option chosen')
        context['voting_errors'] = errors

    if not errors:
        voteinfo = VoteInfo(poll_option_id=polloption_id,
                            member=cur_member,
                            date=datetime.now())
        voteinfo.save()
        context['voting_message'] = u'Vote registered, thank you.'

@member_required_for_post
def topic(request, title_start=None, template_name='cciw/forums/topic.html', topicid=0,
        introtext=None, breadcrumb_extra=None):
    """Displays a topic"""
    if title_start is None:
        raise Exception("No title provided for page")

    ### TOPIC AND POSTS ###
    try:
        topic = Topic.objects.get(id=int(topicid))
    except Topic.DoesNotExist:
        raise Http404

    posts = topic.posts.all()

    ### Feed: ###
    # Requires 'topic' and 'posts'
    resp = feeds.handle_feed_request(request, feeds.topic_post_feed(topic), query_set=posts)
    if resp: return resp

    ### GENERAL CONTEXT ###
    cur_member = get_current_member()

    # Add additional title
    title = topic.subject[0:40]
    if len(title_start) > 0:
        title = title_start + u": " + title
    extra_context = standard_extra_context(title=title)

    if breadcrumb_extra is None:
        breadcrumb_extra = []
    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + topic_breadcrumb(topic.forum, topic))

    if introtext:
        extra_context['introtext'] = introtext

    extra_context['atom_feed_title'] = u"Atom feed for posts in this topic."

    ### PROCESSING ###
    # Process any message that they added.
    resp = process_post(request, topic, None, extra_context)
    if resp is not None:
        return resp
    process_vote(request, topic, extra_context)

    ### TOPIC ###
    extra_context['topic'] = topic
    if topic.open:
        if get_current_member() is not None:
            extra_context['show_message_form'] = True
        else:
            extra_context['login_link'] = login_redirect(request.get_full_path() + '#messageform')

    ### NEWS ITEM ###
    if not topic.news_item_id is None:
        extra_context['news_item'] = topic.news_item

    ### POLL ###
    if topic.poll_id is not None:
        poll = topic.poll
        extra_context['poll'] = poll

        if request.GET.get('showvotebox', None):
            extra_context['show_vote_box'] = True
        else:
            extra_context['show_poll_results'] = True

        extra_context['allow_voting_box'] = \
            (cur_member is None and poll.can_anyone_vote()) or \
            (cur_member is not None and poll.can_vote(cur_member))

    ### PERMISSIONS ###
    if request.user.has_perm('cciwmain.edit_post'):
        extra_context['moderator'] = True

    return object_list(request, posts,
        extra_context=extra_context, template_name=template_name,
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY)

def photoindex(request, gallery, extra_context, breadcrumb_extra):
    "Displays an a gallery of photos"

    ### PHOTOS ###
    photos = gallery.photos.all().select_related('gallery')

    ### FEED ###
    resp = feeds.handle_feed_request(request,
        feeds.gallery_photo_feed(u"CCIW - %s" % extra_context['title']), query_set=photos)
    if resp is not None: return resp

    extra_context['atom_feed_title'] = u"Atom feed for photos in this gallery."
    extra_context['gallery'] = gallery
    extra_context['breadcrumb'] =   create_breadcrumb(breadcrumb_extra + photoindex_breadcrumb(gallery))

    order_by = get_order_option(
        {'aca': ('created_at','id'),
        'dca': ('-created_at','-id'),
        'apc': ('post_count',),
        'dpc': ('-post_count',),
        'alp': ('last_post_at',),
        'dlp': ('-last_post_at',)},
        request, ('created_at', 'id'))
    extra_context['default_order'] = 'aca'
    photos = photos.order_by(*order_by)

    return object_list(request, photos,
        extra_context=extra_context, template_name='cciw/forums/photoindex.html',
        paginate_by=settings.FORUM_PAGINATE_PHOTOS_BY)

@member_required_for_post
def photo(request, photo, extra_context, breadcrumb_extra):
    "Displays a photo"

    ## POSTS ###
    posts = photo.posts.all()

    ### Feed: ###
    resp = feeds.handle_feed_request(request, feeds.photo_post_feed(photo), query_set=posts)
    if resp: return resp

    extra_context['atom_feed_title'] = u"Atom feed for posts on this photo."

    extra_context['breadcrumb'] = create_breadcrumb(breadcrumb_extra + photo_breadcrumb(photo.gallery, photo))
    extra_context['photo'] = photo

    if photo.open:
        if get_current_member() is not None:
            extra_context['show_message_form'] = True
        else:
            extra_context['login_link'] = login_redirect(request.get_full_path() + '#messageform')

    ### PROCESSING ###
    process_post(request, None, photo, extra_context)

    ### PERMISSIONS ###
    if request.user.has_perm('cciwmain.edit_post'):
        extra_context['moderator'] = True

    return object_list(request, posts,
        extra_context=extra_context, template_name='cciw/forums/photo.html',
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY)

def all_posts(request):
    context = standard_extra_context(title=u"Recent posts")
    posts = Post.objects.exclude(posted_at__isnull=True).order_by('-posted_at')

    resp = feeds.handle_feed_request(request, feeds.PostFeed, query_set=posts)
    if resp: return resp

    context['atom_feed_title'] = u"Atom feed for all posts on CCIW message boards."

    return object_list(request, posts,
        extra_context=context, template_name='cciw/forums/posts.html',
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY)

def post(request, id):
    try:
        post = Post.objects.get(pk=id)
    except Post.DoesNotExist:
        raise Http404()
    try:
        url = post.get_forum_url()
    except Topic.DoesNotExist:
        return HttpResponseForbidden("<h1>Access denied</h1><p>Topic is hidden.</p>")
    return HttpResponseRedirect(url)

def all_topics(request):
    context = standard_extra_context(title=u"Recent new topics")
    topics = Topic.objects.exclude(created_at__isnull=True).order_by('-created_at')

    resp = feeds.handle_feed_request(request, feeds.TopicFeed, query_set=topics)
    if resp: return resp

    context['atom_feed_title'] = u"Atom feed for all new topics."

    return object_list(request, topics,
        extra_context=context, template_name='cciw/forums/topics.html',
        paginate_by=settings.FORUM_PAGINATE_POSTS_BY)
