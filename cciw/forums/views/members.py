from datetime import timedelta
import re
import math

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.utils import timezone
from django.utils.safestring import mark_safe

from cciw.cciwmain.common import get_order_option, create_breadcrumb, CciwBaseView, ListView, FeedHandler, get_member_link
from cciw.middleware.threadlocals import get_current_member, remove_member_session
from cciw.cciwmain.decorators import member_required, member_required_for_post, _display_login_form
import cciw.cciwmain.templatetags.bbcode as bbcode
from cciw.cciwmain import feeds


class MemberList(ListView, FeedHandler, CciwBaseView):
    metadata_title = "Members"
    feed_class = feeds.MemberFeed
    template_name = "cciw/members/index.html"
    list_name = 'members'
    paginate_by = 50
    magic_context = {
        'default_order': 'aun',
        'atom_feed_title': "Atom feed for new members"
    }

    def get_queryset(self):
        members = Member.objects.filter(dummy_member=False)
        if self.is_feed_request():
            return members

        if 'online' in self.request.GET:
            members = members.filter(last_seen__gte=(timezone.now() - timedelta(minutes=3)))
        order_by = get_order_option(
            {'adj': ('date_joined',),
             'ddj': ('-date_joined',),
             'aun': ('user_name',),
             'dun': ('-user_name',),
             'arn': ('real_name',),
             'drn': ('-real_name',),
             'als': ('last_seen',),
             'dls': ('-last_seen',)},
            self.request, ('user_name',))
        members = members.order_by(*order_by)

        search = self.request.GET.get('search', '')
        if len(search) > 0:
            members = (members.filter(user_name__icontains=search) | members.filter(real_name__icontains=search))

        return members

index = MemberList.as_view()


class MemberDetail(CciwBaseView):

    template_name = 'cciw/members/detail.html'

    def handle(self, request, user_name):
        if 'logout' in request.POST:
            remove_member_session(request)
            return HttpResponseRedirect(request.path)

        try:
            member = Member.objects.get(user_name=user_name)
        except Member.DoesNotExist:
            raise Http404
        context = {
            'member': member,
            'awards': member.personal_awards.all()
        }
        self.metadata_title = "Member: %s" % member.user_name
        return self.render(context)

detail = MemberDetail.as_view()


# The real work here is done in member_required_for_post,
# and _display_login_form, after that it is just redirecting
@member_required_for_post
def login(request):
    member = get_current_member()
    if member is not None:
        redirect = request.GET.get('redirect', None)
        if not redirect:
            redirect = member.get_absolute_url()
        return HttpResponseRedirect(redirect)
    else:
        return _display_login_form(request, login_page=True)


class SendMessage(CciwBaseView):
    """
    View function that handles the 'send message' form
    """
    # Two modes:
    #  - if user_name is current user, there is a field that
    #    allows them to enter the recipient.
    #  - otherwise, the page is a 'leave message for {{ user_name }}' page.
    # It is easier to handle this without a Django 'Form'.

    template_name = 'cciw/members/messages/send.html'

    def handle(self, request, user_name=None):
        # General setup
        current_member = get_current_member()

        try:
            member = Member.objects.get(user_name=user_name)
        except Member.DoesNotExist:
            raise Http404()

        c = {}

        # Handle input:
        errors = []
        message_sent = False
        preview = None
        message_text = None

        no_messages = False
        to_name = ''

        to = None
        if current_member.user_name != member.user_name:
            to = member
            if to.message_option == Member.MESSAGES_NONE:
                no_messages = True

        if request.method == 'POST':
            # Recipient
            if to is None:
                to_name = request.POST.get('to', '').strip()
                if to_name == '':
                    errors.append('No user name given.')
                else:
                    try:
                        to = Member.objects.get(user_name=to_name)
                    except Member.DoesNotExist:
                        errors.append('The user %s could not be found' % to_name)

            if to is not None and to.message_option == Member.MESSAGES_NONE:
                errors.append('This user has chosen not to receive any messages.')
            else:
                # Message
                message_text = request.POST.get('message', '').strip()
                if message_text == '':
                    errors.append('No message entered.')

                # Always do a preview (for 'preview' and 'send')
                preview = mark_safe(bbcode.bb2xhtml(message_text))
                if len(errors) == 0 and 'send' in request.POST:
                    Message.send_message(to, current_member, message_text)
                    messages.info(request, "Message was sent")
                    return HttpResponseRedirect(request.path)
                else:
                    # Persist text entered, but corrected:
                    message_text = bbcode.correct(message_text)

        # Context vars
        crumbs = [get_member_link(user_name)]
        if current_member.user_name == member.user_name:
            c['mode'] = 'send'
            self.metadata_title = "Send a message"
            crumbs.append('Messages &lt; Send | <a href="inbox/">Inbox</a> | <a href="archived/">Archived</a> &gt;')
            # to_name = to_name (from POST)
        else:
            c['mode'] = 'leave'
            self.metadata_title = "Leave a message for %s" % member.user_name
            crumbs.append('Send message')
            to_name = user_name

        c['breadcrumb'] = create_breadcrumb(crumbs)
        c['member'] = member
        c['to'] = to_name
        c['preview'] = preview
        c['errors'] = errors
        c['message_sent'] = message_sent
        c['message_text'] = message_text
        c['no_messages'] = no_messages

        return self.render(c)

send_message = member_required(SendMessage.as_view())


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


class MessageList(ListView, CciwBaseView):
    """
    View to display inbox or archived messages.
    """
    template_name = 'cciw/members/messages/index.html'
    paginate_by = settings.MEMBERS_PAGINATE_MESSAGES_BY
    list_name = 'member_messages'
    box = None  # must be supplied at some point

    def handle(self, request, user_name=None):
        # Initial common setup
        try:
            member = Member.objects.get(user_name=user_name)
        except Member.DoesNotExist:
            raise Http404

        current_member = get_current_member()
        if current_member is None or user_name != current_member.user_name:
            return HttpResponseForbidden('<h1>Access denied</h1>')

        if request.method == "POST":
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
            message_count = member.messages_received.filter(box=self.box).count()
            page = int(request.GET.get('page', 1))
            last_page = int(math.ceil(float(message_count) / settings.MEMBERS_PAGINATE_MESSAGES_BY))
            last_page = max(last_page, 1)
            if page > last_page:
                # User may have deleted/moved everything on the last page,
                # so need to redirect to avoid a 404
                return HttpResponseRedirect(request.path + "?page=%s" % last_page)

        # Context
        crumbs = [get_member_link(user_name)]
        context = {}
        if self.box == Message.MESSAGE_BOX_INBOX:
            context['title'] = "%s: Inbox" % user_name
            crumbs.append('Messages &lt; <a href="../">Send</a> | Inbox | <a href="../archived/">Archived</a> &gt;')
            context['show_archive_button'] = True
        else:
            context['title'] = "%s: Archived messages" % user_name
            crumbs.append('Messages &lt; <a href="../">Send</a> | <a href="../inbox/">Inbox</a> | Archived &gt;')
            context['show_move_inbox_button'] = True

        context['show_delete_button'] = True
        context['breadcrumb'] = create_breadcrumb(crumbs)

        self.queryset = member.messages_received.filter(box=self.box).order_by('-time').select_related('from_member')
        self.context.update(context)

        # Display paginated list
        return super(MessageList, self).handle(request)

inbox = member_required(MessageList.as_view(box=Message.MESSAGE_BOX_INBOX))
archived_messages = member_required(MessageList.as_view(box=Message.MESSAGE_BOX_SAVED))


class MemberPosts(ListView, FeedHandler, CciwBaseView):
    template_name = 'cciw/members/posts.html'
    paginate_by = settings.FORUM_PAGINATE_POSTS_BY
    list_name = 'posts'

    def get_feed_class(self):
        return feeds.member_post_feed(self.get_member())

    def get_member(self):
        try:
            return Member.objects.get(user_name=self.kwargs['user_name'])
        except Member.DoesNotExist:
            raise Http404

    def get_queryset(self, member=None):
        if member is None:
            member = self.get_member()
        return member.posts.exclude(posted_at__isnull=True).order_by('-posted_at')

    def handle(self, request, user_name=None):
        member = self.get_member()
        self.metadata_title = "Recent posts by %s" % member.user_name
        self.queryset = self.get_queryset(member=member)
        context = {
            'member': member,
            'breadcrumb': create_breadcrumb([get_member_link(user_name),
                                             'Recent posts']),
            'atom_feed_title': "Atom feed for posts from %s" % member.user_name,
        }
        self.context.update(context)

        return super(MemberPosts, self).handle(request)

posts = MemberPosts.as_view()
