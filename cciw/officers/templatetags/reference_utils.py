from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()

@register.filter(name='firstline')
@stringfilter
def firstline(value):
    # Assumes autoescape is on.
    parts = map(escape, value.strip().split("\n"))
    return mark_safe("<div class='firstline'>%s</div><div class='hidden addrblock'>%s</div>" % (parts[0], '<br />'.join(parts[1:])))

@register.filter(name='indent')
@stringfilter
def indent(value, arg=1):
    """
    Template filter to add the given number of spaces to the beginning of
    each line. Useful for keeping markup pretty, plays well with Markdown.

    Usage:
    {{ content|indent:"2" }}
    """
    import re
    regex = re.compile("^", re.M)
    return re.sub(regex, " "*int(arg), value)
