from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@stringfilter
def rtflinebreaks(value):
    "Converts newlines into RTF \lines"
    return value.replace('\n', '{\line}')

register.filter(rtflinebreaks)
