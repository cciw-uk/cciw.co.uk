from django.core import template
from cciw.apps.cciw.common import standard_subs
from cciw.apps.cciw.utils import get_member_link, obfuscate_email

class EmailNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        return obfuscate_email(self.nodelist.render(context))

def do_email(parser, token):
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
    bits = token.contents.split(" ", 2)
    return SetVarNode(bits[1], bits[2])
        
register = template.Library()
register.filter(standard_subs)
register.filter(obfuscate_email)
register.tag('email', do_email)
register.tag('memberlink', do_member_link)
register.tag('setvar', do_setvar)
