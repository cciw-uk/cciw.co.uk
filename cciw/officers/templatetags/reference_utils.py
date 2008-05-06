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
