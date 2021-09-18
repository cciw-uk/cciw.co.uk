from django import template
from django.utils.safestring import SafeData, mark_safe

register = template.Library()


@register.tag
def capture(parser, token):
    """{% capture as [foo] %}"""
    bits = token.split_contents()
    if len(bits) != 3:
        raise template.TemplateSyntaxError("'capture' node requires `as (variable name)`.")
    nodelist = parser.parse(('endcapture',))
    parser.delete_first_token()
    return CaptureNode(nodelist, bits[2])


class CaptureNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        if isinstance(output, SafeData):
            # strip() returns a normal unicode object,
            # we need to mark it safe again
            val = mark_safe(output.strip())
        else:
            val = output.strip()
        context[self.varname] = val
        return ''
