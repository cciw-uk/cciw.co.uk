from django import template

from cciw.cciwmain.common import standard_subs
from cciw.sitecontent.models import HtmlChunk

register = template.Library()
register.filter(standard_subs)


@register.simple_tag(takes_context=True)
def htmlchunk(context, name, ignore_missing=False):
    try:
        chunk = HtmlChunk.objects.get(name=name)
    except HtmlChunk.DoesNotExist:
        if not ignore_missing:
            raise
        chunk = None
    if chunk is None:
        return ""
    return chunk.render(context["request"])
