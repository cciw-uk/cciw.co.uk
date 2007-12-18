from django.views.generic import list_detail
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.utils.safestring import mark_safe

from cciw.cciwmain.models import Member, Message
from cciw.cciwmain.common import standard_extra_context, get_order_option, create_breadcrumb
from cciw.middleware.threadlocals import get_current_member, remove_member_session
from cciw.cciwmain.decorators import member_required, same_member_required, member_required_for_post, _display_login_form
from cciw.cciwmain.utils import get_member_link
import cciw.cciwmain.templatetags.bbcode as bbcode
from cciw.cciwmain import feeds

from datetime import datetime, timedelta
import re
import math

def index(request):
    """
    Displays an index of all members.
    """
    members = Member.objects.filter(dummy_member=False)
    
    feed = feeds.handle_feed_request(request, feeds.MemberFeed, query_set=members)
    if feed: return feed

    if (request.GET.has_key('online')):
        members = members.filter(last_seen__gte=(datetime.now() - timedelta(minutes=3)))
    
    extra_context = standard_extra_context(title=u'Members')
    order_by = get_order_option(
        {'adj': ('date_joined',),
        'ddj': ('-date_joined',),
        'aun': ('user_name',),
        'dun': ('-user_name',),
        'arn': ('real_name',),
        'drn': ('-real_name',),
        'als': ('last_seen',),
        'dls': ('-last_seen',)},
        request, ('user_name',))
    members = members.order_by(*order_by)
    extra_context['default_order'] = 'aun'

    try:
        search = request['search']
        if len(search) > 0:
            members = (members.filter(user_name__icontains=search) | members.filter(real_name__icontains=search))
    except KeyError:
        pass

    extra_context['atom_feed_title'] = u"Atom feed for new members."
    
    return list_detail.object_list(request, members,
        extra_context=extra_context, 
        template_name='cciw/members/index.html',
        paginate_by=50,
        allow_empty=True)

def detail(request, user_name):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
    
    if request.POST:
        if request.POST.has_key('logout'):
            try:
                remove_member_session(request)
            except KeyError:
                pass
        
    c = RequestContext(request, 
        standard_extra_context(title=u"Member: %s" % member.user_name))
    c['member'] = member
    c['awards'] = member.personal_awards.all()
    return render_to_response('cciw/members/detail.html', context_instance=c)

# The real work here is done in member_required_for_post,
# and _display_login_form, after that it is just redirecting
@member_required_for_post
def login(request):
    if request.POST:
        redirect = request.GET.get('redirect', None)
        if not redirect:
            redirect = get_current_member().get_absolute_url()
        return HttpResponseRedirect(redirect)
    else:
        return _display_login_form(request)

@member_required
def send_message(request, user_name):
    """View function that handles the 'send message' form"""

    # Two modes:
    #  - if user_name is current user, have a field that
    #    allows them to enter the recipient
    #  - otherwise, the page is a 'leave message for {{ user_name }} page

    # General setup
    current_member = get_current_member()

    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404

    # Handle input:
    errors = []
    message_sent = False
    preview = None
    message_text = None
    
    no_messages = False
    to_name = u''

    to = None
    if current_member.user_name != member.user_name:
        to = member
        if to.message_option == Member.MESSAGES_NONE:
            no_messages = True

    if request.POST:
        # Recipient
        if to is None:
            to_name = request.POST.get('to', u'').strip()
            if to_name == u'':
                errors.append('No user name given.')
            else:
                try:
                    to = Member.objects.get(user_name=to_name)
                except Member.DoesNotExist:
                    errors.append(u'The user %s could not be found' % to_name)

        if to is not None and to.message_option == Member.MESSAGES_NONE:
            errors.append(u'This user has chosen not to receive any messages.')
        else:
            # Message
            message_text = request.POST.get('message', u'').strip()
            if message_text == u'':
                errors.append(u'No message entered.')
            
            # Always do a preview (for 'preview' and 'send')
            preview = mark_safe(bbcode.bb2xhtml(message_text))
            if len(errors) == 0 and request.POST.has_key('send'):
                Message.send_message(to, current_member, message_text)
                message_sent = True
                message_text = u'' # don't persist.
            else:
                # Persist text entered, but corrected:
                message_text = bbcode.correct(message_text)

    # Context vars
    crumbs = [get_member_link(user_name)]
    if current_member.user_name == member.user_name:
        mode = 'send'
        title = u"Send a message"
        crumbs.append(u'Messages &lt; Send | <a href="inbox/">Inbox</a> | <a href="archived/">Archived</a> &gt;')
        # to_name = to_name (from POST)
    else:
        mode = 'leave'
        title = u"Leave a message for %s" % member.user_name
        crumbs.append(u'Send message')
        to_name = user_name

    c = RequestContext(request, standard_extra_context(title=title))    
    c['breadcrumb'] = create_breadcrumb(crumbs)
    c['member'] = member
    c['to'] = to_name
    c['mode'] = mode
    c['preview'] = preview
    c['errors'] = errors
    c['message_sent'] = message_sent
    c['message_text'] = message_text
    c['no_messages'] = no_messages
    
    return render_to_response('cciw/members/messages/send.html', context_instance=c)

# Utility functions for handling message actions
def _msg_move_inbox(msg):
    msg.box = Message.MESSAGE_BOX_INBOX
    msg.save()
    
def _msg_move_archive(msg):
    msg.box = Message.MESSAGE_BOX_SAVED
    msg.save()

def _msg_del(msg):
    msg.delete()


_id_vars_re = re.compile('msg_(\d+)')

@same_member_required(1)
def message_list(request, user_name, box):
    """View function to display inbox or archived messages."""
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
        
    # Deal with moves/deletes:
    if request.POST:
        ids = [int(m.groups()[0]) for m in map(_id_vars_re.match, request.POST.keys()) if m is not None]
        actions = {
            'delete': _msg_del,
            'inbox': _msg_move_inbox,
            'archive': _msg_move_archive,
        }
        for (name, action) in actions.items():
            if request.POST.get(name):
                for id in ids:
                    try:
                        msg = member.messages_received.get(id=id)
                        action(msg)
                    except Message.DoesNotExist:
                        pass
        message_count = member.messages_received.filter(box=box).count()
        page = request.GET.get('page', 1)
        last_page = int(math.ceil(float(message_count)/settings.MEMBERS_PAGINATE_MESSAGES_BY))
        last_page = max(last_page, 1)
        if page > last_page:
            # User may have deleted/moved everything on the last page,
            # so need to redirect to avoid a 404
            return HttpResponseRedirect(request.path + "?page=%s" % last_page)
            
    
    # Context
    extra_context = standard_extra_context()
    crumbs = [get_member_link(user_name)]
    if box == Message.MESSAGE_BOX_INBOX:
        extra_context['title'] = u"%s: Inbox" % user_name
        crumbs.append(u'Messages &lt; <a href="../">Send</a> | Inbox | <a href="../archived/">Archived</a> &gt;')
        extra_context['show_archive_button'] = True
    else:
        extra_context['title'] = u"%s: Archived messages" % user_name
        crumbs.append(u'Messages &lt; <a href="../">Send</a> | <a href="../inbox/">Inbox</a> | Archived &gt;')
        extra_context['show_move_inbox_button'] = True
     
    extra_context['show_delete_button'] = True
    extra_context['breadcrumb'] = create_breadcrumb(crumbs)
    
    messages = member.messages_received.filter(box=box).order_by('-time')
    
    return list_detail.object_list(request, messages,
        extra_context=extra_context,
        template_name='cciw/members/messages/index.html',
        paginate_by=settings.MEMBERS_PAGINATE_MESSAGES_BY,
        allow_empty=True)

def inbox(request, user_name):
    "Shows inbox for a user"
    return message_list(request, user_name, Message.MESSAGE_BOX_INBOX)
    
def archived_messages(request, user_name):
    return message_list(request, user_name, Message.MESSAGE_BOX_SAVED)

def posts(request, user_name):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
    posts = member.posts.exclude(posted_at__isnull=True).order_by('-posted_at')
    
    resp = feeds.handle_feed_request(request, feeds.member_post_feed(member), 
                                     query_set=posts)
    if resp: return resp
    
    context = standard_extra_context(title=u"Recent posts by %s" % user_name)
    context['member'] = member
    crumbs = [get_member_link(user_name), u'Recent posts']
    context['breadcrumb'] = create_breadcrumb(crumbs)
    context['atom_feed_title'] = u"Atom feed for posts by %s." % user_name

    return list_detail.object_list(request, posts,
        extra_context=context, template_name='cciw/members/posts.html',
        allow_empty=True, paginate_by=settings.FORUM_PAGINATE_POSTS_BY)

