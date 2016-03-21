from django import template
from cciw.sitecontent.models import HtmlChunk
from cciw.cciwmain.common import standard_subs


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


register = template.Library()
register.filter(standard_subs)
register.tag('htmlchunk', do_htmlchunk)
