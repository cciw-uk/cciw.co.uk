from django.core import template
from cciw.apps.cciw.common import *

def obfuscate_email(email):
	# TODO - make into javascript linky thing?
	return email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ')

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

def bb2html(value, _):
	"""Converts message board 'BB code'-like formatting into HTML"""
	emoticons = (
		('0:-)','angel.gif'),
		('O:-)','angel.gif'),
		(':angel:','angel.gif'),
		(':)','smile.gif'),
		(':(','sad.gif'),
		(':D','grin.gif'),
		(':p','tongue.gif'),
		(';)','wink.gif'),
		(':-)','smile.gif'),
		(':-(', 'sad.gif'),
		(':-D', 'grin.gif'),
		(':-P', 'tongue.gif'),
		(':-p', 'tongue.gif'),
		(':-/', 'unsure.gif'),
		(':-\\', 'unsure.gif'),
		(';-)', 'wink.gif'),
		(':-$', 'confused.gif'),
		(':-S', 'confused.gif'),
		('B-)', 'cool.gif'),
		(':lol:', 'lol.gif'),
		(':batman:', 'batman.gif'),
		(':rolleyes:', 'rolleyes.gif'),
		(':icymad:', 'bluemad.gif'),
		(':mad:', 'mad.gif'),
		(':crying:', 'crying.gif'),
		(':eek:', 'eek.gif'),
		(':eyebrow:', 'eyebrow.gif'),
		(':grim:', 'grim_reaper.gif'),
		(':idea:', 'idea.gif'),
		(':rotfl:', 'rotfl.gif'),
		(':shifty:', 'shifty.gif'),
		(':sleep:', 'sleep.gif'),
		(':thinking:', 'thinking.gif'),
		(':wave:', 'wave.gif'),
		(':bow:', 'bow.gif'),
		(':sheep:',  'sheep.gif'),
		(':santa:',  'santaclaus.gif'),
		(':anvil:', 'anvil.gif'),
		(':bandit:', 'bandit.gif'),
		(':chop:', 'behead.gif'),
		(':biggun:', 'biggun.gif'),
		(':mouthful:', 'blowingup,gif'),
		(':gun:', 'bluekillsred.gif'),
		(':box:', 'boxing.gif'),
		(':gallows:', 'hanged.gif'),
		(':jedi:', 'lightsaber1.gif'),
		(':bosh:', 'mallet1.gif'),
		(':saw:', 'saw.gif'),
		(':stupid:', 'youarestupid.gif')
	)

def standard_subs_filter(value, _):
	return standard_subs(value)

template.register_filter('standard_subs', standard_subs_filter, False)
template.register_filter('obfuscate_email', obfuscate_email_filter, False)
template.register_tag('email', do_email)
