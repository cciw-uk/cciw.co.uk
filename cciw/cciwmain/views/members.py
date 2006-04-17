from django.views.generic import list_detail
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings

from cciw.cciwmain.models import Member, Message
from cciw.cciwmain.common import standard_extra_context, get_order_option, create_breadcrumb
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain.decorators import member_required, same_member_required
from cciw.cciwmain.utils import get_member_link
import cciw.cciwmain.templatetags.bbcode as bbcode
from cciw.cciwmain import feeds

from datetime import datetime, timedelta
import re

def index(request):
    members = Member.visible_members.filter(dummy_member=False)
    
    feed = feeds.handle_feed_request(request, feeds.MemberFeed, query_set=members)
    if feed: return feed

    if (request.GET.has_key('online')):
        members = members.filter(last_seen__gte=(datetime.now() - timedelta(minutes=3)))
    
    extra_context = standard_extra_context(title='Members')
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

    return list_detail.object_list(request, members,
        extra_context=extra_context, 
        template_name='cciw/members/index.html',
        paginate_by=50,
        allow_empty=True)

def detail(request, user_name):
    try:
        member = Member.visible_members.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
    
    if request.POST:
        if request.POST.has_key('logout'):
            try:
                import cciw.middleware.threadlocals
                del request.session['member_id']
                del cciw.middleware.threadlocals._thread_locals.member
            except KeyError:
                pass
        
    c = RequestContext(request, 
        standard_extra_context(title="Member: " + member.user_name))
    c['member'] = member
    c['awards'] = member.personal_awards.all()
    return render_to_response('cciw/members/detail.html', context_instance=c)
    
def login(request):
    c = RequestContext(request, standard_extra_context(title="Login"))
    redirect = request.GET.get('redirect', None)
    c['isFromRedirect'] = (redirect is not None)
    if request.POST:
        try:
            member = Member.visible_members.get(user_name=request.POST['user_name'])
            if member.check_password(request.POST['password']):
                request.session['member_id'] = member.user_name
                member.last_seen = datetime.now()
                member.save()
                redirect_url = redirect or member.get_absolute_url()
                return HttpResponseRedirect(redirect_url)
            else:
                c['loginFailed'] = True
        except Member.DoesNotExist:
            c['loginFailed'] = True
    return render_to_response('cciw/members/login.html', context_instance=c)

@member_required
def send_message(request, user_name):
    """View function that handles the 'send message' form"""

    # Two modes:
    #  - if user_name is current user, have a field that
    #    allows them to enter the recipient
    #  - otherwise, the page is a 'leave message for {{ user_name }} page

    # General setup
    current_member = get_current_member()

    # Handle input:
    errors = []
    message_sent = False
    preview = None
    message_text = None
    
    try:
        member = Member.visible_members.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404

    to_name = ''
    if request.POST:
        to = None
        # Recipient
        if current_member.user_name != member.user_name:
            to = member
        else:
            to_name = request.POST.get('to', '').strip()
            if to_name == '':
                errors.append('No user name given.')
            else:
                try:
                    to = Member.visible_members.get(user_name=to_name)
                except Member.DoesNotExist:
                    errors.append('The user %s could not be found' % to_name)

        # Message
        message_text = request.POST.get('message', '').strip()
        if message_text == '':
            errors.append('No message entered.')
        
        # Always do a preview (for 'preview' and 'send')
        preview = bbcode.bb2xhtml(message_text)
        if len(errors) == 0 and request.POST.has_key('send'):
            msg = Message(to_member=to, from_member=current_member,
                text=message_text, time=datetime.now(),
                box=Message.MESSAGE_BOX_INBOX)
            msg.save()
            message_sent = True
            message_text = '' # don't persist.
        else:
            # Persist text entered, but corrected:
            message_text = bbcode.correct(message_text)

    # Context vars
    crumbs = [get_member_link(user_name)]
    if current_member.user_name == member.user_name:
        mode = 'send'
        title = "Send a message"
        crumbs.append('Messages &lt; Send | <a href="inbox/">Inbox</a> | <a href="archived/">Archived</a> &gt;')
        # to_name = to_name (from POST)
    else:
        mode = 'leave'
        title = "Leave a message for %s" % member.user_name
        crumbs.append('Send message')
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

@same_member_required(1)
def message_list(request, user_name, box):
    """View function to display inbox or archived messages."""
    try:
        member = Member.visible_members.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
        
    # Deal with moves/deletes:
    if request.POST:
        id_vars_re = re.compile('msg_\d+')
        ids = [int(var[4:]) for var in request.POST.keys() if id_vars_re.match(var)]
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
    
    # Context
    extra_context = standard_extra_context()
    crumbs = [get_member_link(user_name)]
    if box == Message.MESSAGE_BOX_INBOX:
        extra_context['title'] = "%s: Inbox" % user_name
        crumbs.append('Messages &lt; <a href="../">Send</a> | Inbox | <a href="../archived/">Archived</a> &gt;')
        extra_context['show_archive_button'] = True
    else:
        extra_context['title'] = "%s: Archived messages" % user_name
        crumbs.append('Messages &lt; <a href="../">Send</a> | <a href="../inbox/">Inbox</a> | Archived &gt;')
        extra_context['show_move_inbox_button'] = True
     
    extra_context['show_delete_button'] = True
    extra_context['breadcrumb'] = create_breadcrumb(crumbs)
    
    messages = member.messages_received.filter(box=box).order_by('-time')
    
    return list_detail.object_list(request, messages,
        extra_context=extra_context,
        template_name='cciw/members/messages/index.html',
        paginate_by=20,
        allow_empty=True)

def inbox(request, user_name):
    return message_list(request, user_name, Message.MESSAGE_BOX_INBOX)
    
def archived_messages(request, user_name):
    return message_list(request, user_name, Message.MESSAGE_BOX_SAVED)

def posts(request, user_name):
    try:
        member = Member.visible_members.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
    
    context = standard_extra_context(title="Recent posts by %s" % user_name)
    crumbs = [get_member_link(user_name), 'Recent posts']
    context['breadcrumb'] = create_breadcrumb(crumbs)
    posts = member.posts.exclude(posted_at__isnull=True).order_by('-posted_at')
    
    feed = feeds.handle_feed_request(request, feeds.PostFeed, query_set=posts)
    if feed: return feed

    return list_detail.object_list(request, posts,
        extra_context=context, template_name='cciw/members/posts.html',
        allow_empty=True, paginate_by=settings.FORUM_PAGINATE_POSTS_BY)
