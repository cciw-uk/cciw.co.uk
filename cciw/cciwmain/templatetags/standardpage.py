from django.utils.http import urlquote, urlencode
from django import template
from cciw.cciwmain.models import HtmlChunk, Member, Post, Topic, Photo
from cciw.cciwmain.common import standard_subs, get_current_domain
from cciw.cciwmain.utils import obfuscate_email
from cciw.middleware.threadlocals import get_current_member
from django.utils.html import escape
from django.conf import settings

class EmailNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        return obfuscate_email(self.nodelist.render(context))

def do_email(parser, token):
    """
    Obfuscates the email address between the
    'email' and 'endemail' tags.
    """
    nodelist = parser.parse(('endemail',))
    parser.delete_first_token()
    return EmailNode(nodelist)

class RenderHtmlChunk(template.Node):
    def __init__(self, chunk_name):
        self.chunk_name = chunk_name

    def render(self, context):
        chunk = getattr(self, 'chunk', None)
        if chunk is None:
            chunk = HtmlChunk.objects.get(name=self.chunk_name)
            self.chunk = chunk
        return chunk.render(context['request'])

def do_htmlchunk(parser, token):
    """
    Renders an HtmlChunk. It takes a single argument,
    the name of the HtmlChunk to find.
    """
    bits = token.contents.split(" ", 1)
    return RenderHtmlChunk(bits[1])

class AtomFeedLink(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            return u'<link rel="alternate" type="application/atom+xml" href="%(url)s?format=atom" title="%(title)s" />' \
            % {'url': context['request'].path, 'title': title }
        else:
            return u''

class AtomFeedLinkVisible(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            thisurl = context['request'].path
            thisfullurl = 'https://%s%s' % (get_current_domain(), thisurl)
            return (u'<a class="atomlink" href="%(atomurl)s" rel="external" title="%(atomtitle)s" >' +
                    u' <img src="%(atomimgurl)s" alt="Feed icon" /></a> |') \
            % dict(atomurl="%s?format=atom" % thisurl,
                   atomtitle=title,
                   atomimgurl="%simages/feed.gif" % settings.STATIC_URL,
               )
        else:
            return ''


register = template.Library()
register.filter(standard_subs)
register.filter(obfuscate_email)
register.tag('email', do_email)
register.tag('htmlchunk', do_htmlchunk)
register.tag('atomfeedlink', AtomFeedLink)
register.tag('atomfeedlinkvisible', AtomFeedLinkVisible)
