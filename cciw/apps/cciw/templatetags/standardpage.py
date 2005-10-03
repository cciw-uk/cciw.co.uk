from django.core import template
from cciw.apps.cciw.common import standard_subs
from cciw.apps.cciw.utils import get_member_link, obfuscate_email

def obfuscate_email_filter(email, _):
	return obfuscate_email(email)

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
		userName = self.nodelist.render(context)
		return get_member_link(userName)
	
def do_member_link(parser, token):
	nodelist = parser.parse(('endmemberlink',))
	parser.delete_first_token()
	return MemberLinkNode(nodelist)

def standard_subs_filter(value, _):
	return standard_subs(value)

template.register_filter('standard_subs', standard_subs_filter, False)
template.register_filter('obfuscate_email', obfuscate_email_filter, False)
template.register_tag('email', do_email)
template.register_tag('memberlink', do_member_link)
