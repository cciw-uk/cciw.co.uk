#####################################################################
##	Copyright (c) 2005, Luke Plant <L.Plant.98@cantab.net>
##	 All rights reserved.
##	Redistribution and use in source and binary forms, with or without
##	modification, are permitted provided that the following conditions are
##	met: Redistributions of source code must retain the above copyright
##	notice, this list of conditions and the following disclaimer.
##	Redistributions in binary form must reproduce the above copyright
##	notice, this list of conditions and the following disclaimer in the
##	documentation and/or other materials provided with the distribution.
##	Neither the name of the <ORGANIZATION> nor the names of its
##	contributors may be used to endorse or promote products derived from
##	this software without specific prior written permission. THIS SOFTWARE
##	IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
##	EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
##	IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
##	PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
##	CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
##	EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
##	PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
##	PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
##	LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
##	NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
##	SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

##########################################################################
## Module to convert BBCode to XHTML, featuring:
##
## 1) full XHTML compliance, including prohibited elements
## 2) intelligent handling/preserving of whitespace
## 3) emoticons, with intelligent handling for tricky cases
## 4) ability to render out corrected BBCode as well as XHTML
## 5) XHTML outputed can be inserted into <body>, <div>, <td>
##    and any other elements that allow block level tags
##
## IMPLEMENTATION NOTES
## 
## 1) I have implemented what I needed and used for my own needs,
##    which isn't necessarily 'standard' bbcode, if such a thing exists
## 2) There are some definitely web site specific extensions
##    e.g. [email], [member], the rendering of [quote=person]
## 3) 'Missing' tags - [img] - but should be easy to add


import re
from cciw.apps.cciw.utils import get_member_link, obfuscate_email

##### CONSTANTS #####
from cciw.apps.cciw.settings import CCIW_MEDIA_ROOT
EMOTICONS_ROOT = CCIW_MEDIA_ROOT + 'images/emoticons/'

##### UTILITY FUNCTIONS #####
def escape(html):
	"Returns the given HTML with ampersands, quotes and carets encoded"
	if not isinstance(html, basestring):
		html = str(html)
	return html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

###### UTILITY CLASSES ######
class BBTag:
	"Contains info about an allowed tag and tags it can contain"
	def __init__(self, name, allowed_children, implicit_tag, self_closing=False, prohibited_elements = None,
		discardable = False):
		if prohibited_elements is None:
			self.prohibited_elements = ()
		else:
			self.prohibited_elements = prohibited_elements
		self.self_closing = self_closing
		self.name = name
		self.implicit_tag = implicit_tag
		self.allowed_children = allowed_children
		self.discardable = discardable

###### DATA ######

colors = ('aqua', 'black', 'blue', 'fuchsia', 'gray', 'green', 'lime', 'maroon', 'navy', 'olive', 
	'purple', 'red', 'silver', 'teal', 'white', 'yellow')
colorregexp = re.compile(r'#[0-9A-F]{6}')

# 'text' is a dummy entry for text nodes
inline_tags = ('b', 'i', 'color', 'member', 'email', 'url', 'br', 'text', 'img', 'softbr', 'emoticon')
block_level_tags = ('p', 'quote', 'list', 'pre', 'code')
other_tags = ('*',)

anchor_tags = ('member', 'email', 'url')

# Rules, defined so that the output after translation will be 
# XHTML compatible. Other rules are implicit in the parsing routines.
# Note that some bbtags can adapt to their context in the rendering
# phase in order to generate correct XHTML, so have slacker rules than normal
taginfo = (
	BBTag('br', (), 'p', self_closing = True, discardable = True), 	# <br/>
	BBTag('softbr', (), 'p', self_closing = True, discardable = True), # <br/>, but can adapt during render
	BBTag('emoticon', ('text',), 'p'),							# <img/>,  but can adapt
	BBTag('b', inline_tags, 'p'),								# <b>
	BBTag('i', inline_tags, 'p'),								# <i>
	BBTag('color', inline_tags, 'p'),							# <span>
	BBTag('member', ('text',), 'p' ),							# <a>
	BBTag('email', ('text',), 'p'),								# <a>
	BBTag('url', ('text',), 'p'),								# <a>
	BBTag('p', inline_tags, None),								# <p>
	BBTag('quote', block_level_tags + ('softbr',), None),			# <blockquote>
	BBTag('list', ('*', 'softbr'), None),						# <ul>
	BBTag('pre', inline_tags, None, prohibited_elements = ('img', 'big', 'small', 'sub', 'sup')), # <pre> (only img currently implemented out of those prohibited elements
	BBTag('code', inline_tags, None, prohibited_elements = ('img', 'big', 'small', 'sub', 'sup')), # <pre>
	BBTag('*', inline_tags + block_level_tags, 'list')
)

# Make a dictionary
tagdict = {}
for t in taginfo:
	if t.name != 'text':
		tagdict[t.name] = t

# Make list of valid tags
validtags = [t.name for t in taginfo]

# Regexp
bbtagregexp = re.compile(r'\[\/?([A-Za-z\*]+)(=[^\]]+)?\]')

# Translation tables
# value is either the html element to output or a function
# to call that takes the BBTagNode and returns the output.
bb2xhtml_map = {
	'br': 'br/',
	'b': 'b',
	'i': 'i',
	'p': 'p',
	'pre': 'pre',
	'code': 'pre', # TODO - add a 'class' attribute
	'list': 'ul',
	'*': 'li',
	'quote': 'blockquote', # TODO - handle the parameter
	# TODO - the hard ones
}

emoticons = {
		'0:-)': 'angel.gif',
		'O:-)':'angel.gif',
		':angel:':'angel.gif',
		':)':'smile.gif',
		':(':'sad.gif',
		':D':'grin.gif',
		':p':'tongue.gif',
		';)':'wink.gif',
		':-)':'smile.gif',
		':-(': 'sad.gif',
		':-D': 'grin.gif',
		':-P': 'tongue.gif',
		':-p': 'tongue.gif',
		':-/': 'unsure.gif',
		':-\\': 'unsure.gif',
		';-)': 'wink.gif',
		':-$': 'confused.gif',
		':-S': 'confused.gif',
		'B-)': 'cool.gif',
		':lol:': 'lol.gif',
		':batman:': 'batman.gif',
		':rolleyes:': 'rolleyes.gif',
		':icymad:': 'bluemad.gif',
		':mad:': 'mad.gif',
		':crying:': 'crying.gif',
		':eek:': 'eek.gif',
		':eyebrow:': 'eyebrow.gif',
		':grim:': 'grim_reaper.gif',
		':idea:': 'idea.gif',
		':rotfl:': 'rotfl.gif',
		':shifty:': 'shifty.gif',
		':sleep:': 'sleep.gif',
		':thinking:': 'thinking.gif',
		':wave:': 'wave.gif',
		':bow:': 'bow.gif',
		':sheep:':  'sheep.gif',
		':santa:':  'santaclaus.gif',
		':anvil:': 'anvil.gif',
		':bandit:': 'bandit.gif',
		':chop:': 'behead.gif',
		':biggun:': 'biggun.gif',
		':mouthful:': 'blowingup,gif',
		':gun:': 'bluekillsred.gif',
		':box:': 'boxing.gif',
		':gallows:': 'hanged.gif',
		':jedi:': 'lightsaber1.gif',
		':bosh:': 'mallet1.gif',
		':saw:': 'saw.gif',
		':stupid:': 'youarestupid.gif',
}

###### PARSING CLASSES AND FUNCTIONS ######
class BBNode:
	"Abstract base class for a node of BBcode."
	def __init__(self, parent):
		self.parent = parent
		self.children = []
		
	def renderChildrenXhtml(self):
		return "".join([n.renderXhtml() for n in self.children])

class BBRootNode(BBNode):
	"Represents a root node"
	def __init__(self):
		BBNode.__init__(self, None)
		self.children = []
	
	def renderXhtml(self):	
		return self.renderChildrenXhtml()

	def allows(self, tagname):
		# Rule for HTML BODY element
		return tagname in block_level_tags

	
class BBTextNode(BBNode):
	"A text node, containing only plain text"
	def __init__(self, parent, text):
		BBNode.__init__(self, parent)
		self.text = text
		
	def renderXhtml(self):
		return escape(self.text)

	def allows(self, tagname):
		return False  	# text nodes are always leaf nodes

class BBTagNode(BBNode):
	def __init__(self, parent, name, parameter):
		BBNode.__init__(self, parent)
		self.bbtag = tagdict[name]
		self.parameter = parameter
	
	def prohibited(self, tagname):
		"""returns True if the element 'tagname' is prohibited by
		this node or any parent nodes"""
		if tagname in self.bbtag.prohibited_elements:
			return True
		else:
			if self.parent is None or not hasattr(self.parent, 'prohibited'):
				return False
			else:
				return self.parent.prohibited(tagname)
	
	def allows(self, tagname):
		"Returns true if the tag with 'tagname' can be added to this tag"
		if tagname in self.bbtag.allowed_children:
			# Check prohibited_elements of this and parent tags
			return not self.prohibited(tagname)
		else:
			return False
		
	def renderXhtml(self):
		htmlTag = bb2xhtml_map.get(self.bbtag.name, None)		
		if htmlTag is None:
			# All tags that need special work
			##############################
			if self.bbtag.name == 'softbr':
				if self.parent.allows('br'):
					return '<br/>'
				else:
					return '\n'
			##############################		
			elif self.bbtag.name == 'emoticon':
				if len(self.children) == 0:
					return ''
				emoticon = self.children[0].text   # child is always a BBTextNode
				if self.parent.allows('img'):
					try:
						imagename = emoticons.get(emoticon,'')
					except KeyError:
						return ''
					else:
						return '<img src="' + EMOTICONS_ROOT + imagename + '" alt="' + escape(emoticon) + '" />'
				else:
					return emoticon
			##############################
			elif self.bbtag.name == 'member':
				if len(self.children) == 0:
					return ''
				else:
					user = escape(self.children[0].text.strip().replace(" ",""))
					if len(user) == 0:
						return ''
					return get_member_link(user)
			##############################
			elif self.bbtag.name == 'url':
				if len(self.children) == 0:
					return ''
				if not self.parameter is None:
					url = self.parameter.strip()
				else:
					url = self.children[0].text.strip()
				linktext = self.children[0].text.strip()
				return '<a href="' + escape(url) + '">' + escape(linktext) + '</a>'
			##############################
			elif self.bbtag.name == 'color':
				if len(self.children) > 0:
					if self.parameter.lower() in colors or \
						not colorregexp.match(self.parameter) is None:
						return '<span style="color: ' + self.parameter +  ';">' + self.renderChildrenXhtml() + '</span>'
					else:
						return self.renderChildrenXhtml()
				return ''
			##############################
			elif self.bbtag.name == 'email':
				if len(self.children) > 0:
					return obfuscate_email(escape(self.children[0].text.strip()))
				else:
					return ''
			
			##############################
			else:
				raise NotImplementedError('Unknown tag: ' + self.bbtag.name)
		else:
			if self.bbtag.self_closing:
				return '<' + htmlTag + '>'
			else:
				if len(self.children) > 0:
					return '<' + htmlTag + '>' + self.renderChildrenXhtml() + '</' + htmlTag + '>'
		return ''
		
class BBCodeParser:
	def __init__(self, bbcode):
		self.rootNode = BBRootNode()
		self.currentNode = self.rootNode
		self.bbcode = bbcode
		self.parse()
		
	def pushTextNode(self, text):
		if not self.currentNode.allows('text'):
			# e.g. text after [list] but before [*]
			# or after [quote].
			# Only get here if BBRootNode or BBTagNode is current
			if len(text.strip()) == 0:
				# Whitespace, append anyway
				self.currentNode.children.append(BBTextNode(self.currentNode, text))
			else:
				if self.currentNode.allows('p'):
					self.currentNode.children.append(BBTagNode(self.currentNode, 'p',''))
					self.descend()
				else:
					self.ascend()
				self.pushTextNode(text)
		else:
			self.currentNode.children.append(BBTextNode(self.currentNode, text))
			# text nodes are never open, do don't bother descending
			
	def descend(self):
		self.currentNode = self.currentNode.children[-1]
		
	def ascend(self):
		self.currentNode = self.currentNode.parent
	
	def pushTagNode(self, name, parameter):
		if not self.currentNode.allows(name):
			newTag = tagdict[name]
			if newTag.discardable:
				return
			elif (self.currentNode == self.rootNode or \
				self.currentNode.bbtag.name in block_level_tags) and\
				not newTag.implicit_tag is None:
				
				# E.g. [*] inside root, or [*] inside [block]
				# or inline inside root
				# Add an implicit tag if possible
				self.pushTagNode(newTag.implicit_tag, '')
				self.pushTagNode(name, parameter)					
			else:
				# e.g. block level in inline etc. - traverse up the tree
				self.currentNode = self.currentNode.parent
				self.pushTagNode(name, parameter)
		else:
			node = BBTagNode(self.currentNode, name, parameter)
			self.currentNode.children.append(node)
			if not node.bbtag.self_closing:
				self.descend()

	def popTagNode(self, name):
		"Pops the stack back to the specified tag, closing that tag"
		tempNode = self.currentNode
		while True:
			if tempNode == self.rootNode:
				# Give up, effectively discarding the closing tag
				break
			if hasattr(tempNode, 'bbtag'):
				if tempNode.bbtag.name == name:
					# found it
					self.currentNode = tempNode
					self.ascend()
					break
			tempNode = tempNode.parent
			continue
	
	def parse(self):
		# Replace newlines with 'soft' brs
		self.bbcode = self.bbcode.replace("\n", '[softbr]')
		
		# Replace emoticons with context-sensitive emoticon tags
		for emoticon in emoticons.keys():
			self.bbcode = self.bbcode.replace(emoticon, '[emoticon]' + emoticon + '[/emoticon]')
			
		pos = 0
		while pos < len(self.bbcode):		
			m = bbtagregexp.search(self.bbcode, pos)
			if not m is None:
				# push all text up to the start of the match
				self.pushTextNode(self.bbcode[pos:m.start()])
				
				# push the tag itself
				tagname = m.groups()[0]
				parameter = m.groups()[1]
				if not parameter is None and len(parameter) > 0:
					parameter = parameter[1:] # strip the equals
				if tagname in validtags:
					# genuine tag, push it
					if m.group().startswith('[/'):
						# closing
						self.popTagNode(tagname)
					else:
						# opening
						self.pushTagNode(tagname, parameter)
				pos = m.end()
			else:
				# push all remaining text
				self.pushTextNode(self.bbcode[pos:])
				pos = len(self.bbcode)
		
	def renderXhtml(self):
		return self.rootNode.renderXhtml()

def bb2xhtml(bbcode):
	"Render bbcode as XHTML"
	parser = BBCodeParser(bbcode)
	return parser.renderXhtml()
