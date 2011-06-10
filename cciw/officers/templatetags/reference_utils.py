from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


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
