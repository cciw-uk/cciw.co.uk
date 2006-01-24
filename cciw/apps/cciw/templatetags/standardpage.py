from django.core import template
from django.models.sitecontent import htmlchunks
from cciw.apps.cciw.common import standard_subs
from cciw.apps.cciw.utils import get_member_link, obfuscate_email


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

class MemberLinkNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        user_name = self.nodelist.render(context)
        return get_member_link(user_name)
    
def do_member_link(parser, token):
    """
    Creates a link to a member, using the member name between the 
    'memberlink' and 'endmemberlink' tags.
    """
    nodelist = parser.parse(('endmemberlink',))
    parser.delete_first_token()
    return MemberLinkNode(nodelist)
    
class SetVarNode(template.Node):
    def __init__(self, varname, varval):
        self.varname = varname
        self.varval = varval
    def render(self, context):
        context[self.varname] = template.resolve_variable(self.varval, context)
        return ''

        
def do_setvar(parser, token):
    """
    Sets a variable in the context.  The first argument 
    must be the variable name, the second the variable value
    as a literal or a variable."""
    bits = token.contents.split(" ", 2)
    return SetVarNode(bits[1], bits[2])

class AddHtmlChunk(template.Node):
    def __init__(self, context_var, chunk_name):
        self.context_var = context_var
        self.chunk = htmlchunks.get_object(name__exact=chunk_name)
        
    def render(self, context):
        self.chunk.render(context, self.context_var)
        return ''
    
def do_addhtmlchunk(parser, token):
    """
    Adds an HtmlChunk into the context.  This should be
    used after 'load' statements and before 'extends'.
    It takes two arguments, the name of the context variable
    to set and the name of the HtmlChunk to find.
    
    A reference to the HtmlChunk is also added to the 
    pagevars['html_chunks'] variable.
    """
    bits = token.contents.split(" ", 2)
    return AddHtmlChunk(bits[1], bits[2])

        
register = template.Library()
register.filter(standard_subs)
register.filter(obfuscate_email)
register.tag('email', do_email)
register.tag('memberlink', do_member_link)
register.tag('setvar', do_setvar)
register.tag('addhtmlchunk', do_addhtmlchunk)

