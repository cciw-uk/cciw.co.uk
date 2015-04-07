from django import template
from cciw.sitecontent.models import HtmlChunk
from cciw.cciwmain.common import standard_subs
from cciw.cciwmain.utils import obfuscate_email
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
    def __init__(self, chunk_name, ignore_missing=False):
        self.chunk_name = chunk_name
        self.ignore_missing = ignore_missing

    def render(self, context):
        chunk = getattr(self, 'chunk', None)
        if chunk is None:
            try:
                chunk = HtmlChunk.objects.get(name=self.chunk_name)
            except HtmlChunk.DoesNotExist:
                if not self.ignore_missing:
                    raise
                chunk = None
            self.chunk = chunk
        if chunk is None:
            return ''
        return chunk.render(context['request'])


def do_htmlchunk(parser, token):
    """
    Renders an HtmlChunk. It takes a single argument,
    the name of the HtmlChunk to find.

    If 'ignoremissing' is passed as second argument, errors will be ignored.
    """
    bits = token.contents.split(" ")
    if len(bits) == 2:
        ignore_missing = False
    else:
        ignore_missing = bits[2] == 'ignoremissing'
    return RenderHtmlChunk(bits[1], ignore_missing=ignore_missing)

class AtomFeedLink(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            return '<link rel="alternate" type="application/atom+xml" href="%(url)s?format=atom" title="%(title)s" />' \
            % {'url': context['request'].path, 'title': title }
        else:
            return ''

class AtomFeedLinkVisible(template.Node):
    def __init__(self, parser, token):
        pass
    def render(self, context):
        title = context.get('atom_feed_title', None)
        if title:
            thisurl = context['request'].path
            return ('<a class="atomlink" href="%(atomurl)s" rel="external" title="%(atomtitle)s" >' +
                    ' <img src="%(atomimgurl)s" alt="Feed icon" /></a> |') \
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
