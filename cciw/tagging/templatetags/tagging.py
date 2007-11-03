from django import template
from cciw.tagging import utils
from cciw.tagging.models import Tag

register = template.Library()

class TagSummaryNode(template.Node):
    def __init__(self, object_var_name, output_var_name):
        self.object_var_name = object_var_name
        self.output_var_name = output_var_name
        
    def render(self, context):
        try:
            obj = template.resolve_variable(self.object_var_name, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.output_var_name] = Tag.objects.get_tag_summaries(target=obj)
        return ''

def do_get_tag_summaries(parser, token):
    """
    Gets tag summaries for an object, populating the context with
    a TagSummaryCollection using the named defined in the 'as' clause.
    
    Syntax::
    
        {% get_tag_summaries for [object] as [varname] %}
        
    Example usage::
        
        {% get_tag_summaries for post as post_tags %}
        
    """
    tokens = token.contents.split()
    # Now tokens is a list like this:
    # ['get_tag_summaries', 'for', 'foo', 'as', 'bar']
    if not len(tokens) == 5:
        raise template.TemplateSyntaxError, "%r tag requires 4 arguments" % tokens[0]
    if tokens[1] != 'for':
        raise template.TemplateSyntaxError, "First argument in %r tag must be 'for'" % tokens[0]
    if tokens[3] != 'as':
        raise template.TemplateSyntaxError, "Third argument in %r must be 'as'" % tokens[0]

    return TagSummaryNode(tokens[2], tokens[4])

register.tag('get_tag_summaries', do_get_tag_summaries)
