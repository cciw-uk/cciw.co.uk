from django.views.generic import list_detail
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext

from cciw.cciwmain.models import Member, Message
from cciw.cciwmain.common import standard_extra_context, get_order_option, get_current_member, create_breadcrumb, member_required
from cciw.cciwmain.utils import get_member_link
import cciw.cciwmain.templatetags.bbcode as bbcode

from datetime import datetime, timedelta

def index(request):
    members = Member.objects.filter(dummy_member=False, hidden=False) # TODO - depends on authorisation
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
        template_name='cciw/members/index',
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
                del request.session['member_id']
            except KeyError:
                pass
        
    c = RequestContext(request, 
        standard_extra_context(title="Members: " + member.user_name))
    c['member'] = member
    c['awards'] = member.personal_awards
    return render_to_response('cciw/members/detail', context_instance=c)
    
def login(request):
    c = RequestContext(request, standard_extra_context(title="Login"))
    redirect = request.GET.get('redirect', None)
    c['isFromRedirect'] = (redirect is not None)
    if request.POST:
        try:
            member = Member.objects.get(user_name=request.POST['user_name'])
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
    return render_to_response('cciw/members/login', context_instance=c)

@member_required
def send_message(request, user_name):
    """View function that handles the 'send message' form"""

    # Two modes:
    #  - if user_name is current user, have a field that
    #    allows them to enter the recipient
    #  - otherwise, the page is a 'leave message for {{ user_name }} page

    # General setup
    current_member = get_current_member(request)

    # Handle input:
    errors = []
    message_sent = False
    preview = None
    message_text = None
    
    try:
        member = Member.objects.get(user_name=user_name)
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
                    to = Member.objects.get(user_name=to_name)
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
    
    return render_to_response('cciw/members/messages/send', context_instance=c)

def message_list(request, user_name, box):
    """View function to display inbox or archived messages."""
    member = get_current_member(request)
    if member.user_name != user_name:
        return HttpResponseForbidden
    
    crumbs = [get_member_link(user_name)]
    if box == Message.MESSAGE_BOX_INBOX:
        title="%s: Inbox" % user_name
        crumbs.append('Messages &lt; <a href="../">Send</a> | Inbox | <a href="../archived/">Archived</a> &gt;')
    else:
        title="%s: Archived messages" % user_name
        crumbs.append('Messages &lt; <a href="../">Send</a> | <a href="../inbox/">Inbox</a> | Archived &gt;')
    extra_context = standard_extra_context(title=title)
    extra_context['breadcrumb'] = create_breadcrumb(crumbs)
    
    messages = member.messages_received.filter(box=box).order_by('-time')
    
    return list_detail.object_list(request, messages,
        extra_context=extra_context,
        template_name='cciw/members/messages/index',
        paginate_by=30,
        allow_empty=True)

def inbox(request, user_name):
    return message_list(request, user_name, Message.MESSAGE_BOX_INBOX)
    
def archived_messages(request, user_name):
    return message_list(request, user_name, Message.MESSAGE_BOX_SAVED)
