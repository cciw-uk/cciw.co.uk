from django import template
from django.template.defaultfilters import stringfilter
import encodings

register = template.Library()


@stringfilter
def rtflinebreaks(value):
    "Converts newlines into RTF \lines"
    return value.replace('\n', '{\line}')

register.filter(rtflinebreaks)

encoder = encodings.codecs.getencoder('1252')


def unicode_to_rtf(u):
    """Replaces all high characters with \\u escape sequences,
    assuming a Windows 1252 code page"""
    # We will assume Windows code page for now (for maxiumum
    # likelihood of compatibility -- RTF only seems to support
    # the first 65535 chars of unicode anyway).
    # The document should have these codes
    # \ansi\ansicpg1252\uc1
    output = []
    for char in u:
        if ord(char) > 127:
            try:
                encoded = encoder(char)
            except UnicodeEncodeError:
                encoded = encoder('?')
            val = ord(encoded[0])
            if val < 256:
                # use \' method:
                converted = "\\'" + hex(val)[2:]
            else:
                # Don't even know if this works.  The
                # '?' is the alternate rendering, one byte long,
                # to match the '\uc1' directive
                converted = "\\u%d ?" % val
        else:
            converted = str(char)
        output.append(converted)
    return ''.join(output)


@stringfilter
def rtfescape(value):
    "Escapes RTF control characters"

    return unicode_to_rtf(value.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}'))

register.filter(rtfescape)
