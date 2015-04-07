from django import template
from django.utils.safestring import mark_safe
from cciw.cciwmain.decorators import login_redirect
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain.templatetags import bbcode

def bb2html(value):
    """Converts message board 'BB code'-like formatting into HTML"""
    return bbcode.bb2xhtml(value, True)

register = template.Library()
register.filter('bb2html', lambda s: mark_safe(bb2html(s)))

@register.inclusion_tag('cciw/forums/poll_vote_box.html')
def poll_vote_box(request, topic, poll, heading_level):
    """Displays a box for voting in a poll.  The request,
    the topic object and the poll object must be passed in."""

    member = get_current_member()
    context = {
        'poll': poll,
        'member': member,
        'heading_level': heading_level,
        'action_url': topic.get_absolute_url(),
    }

    if poll.can_anyone_vote():
        if member is None:
            context['show_form'] = False
            context['login_link'] = login_redirect(request.get_full_path())
        else:
            if poll.can_vote(member):
                context['show_form'] = True
            else:
                context['show_form'] = False
                context['message'] = '[You cannot vote on this poll]'
    else:
        context['show_form'] = False
        context['message'] = '[This poll is closed for voting]'
    return context
