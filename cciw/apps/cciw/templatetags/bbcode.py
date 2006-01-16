#####################################################################
##    Copyright (c) 2005, Luke Plant <L.Plant.98@cantab.net>
##     All rights reserved.
##    Redistribution and use in source and binary forms, with or without
##    modification, are permitted provided that the following conditions are
##    met: Redistributions of source code must retain the above copyright
##    notice, this list of conditions and the following disclaimer.
##    Redistributions in binary form must reproduce the above copyright
##    notice, this list of conditions and the following disclaimer in the
##    documentation and/or other materials provided with the distribution.
##    Neither the name of the <ORGANIZATION> nor the names of its
##    contributors may be used to endorse or promote products derived from
##    this software without specific prior written permission. THIS SOFTWARE
##    IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
##    EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
##    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
##    PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
##    CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
##    EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
##    PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
##    PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
##    LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
##    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
##    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

##########################################################################
## Module to convert BBCode to XHTML, featuring:
##
## 1) full XHTML compliance, including prohibited elements
## 2) intelligent handling/preserving of whitespace
## 3) emoticons, with intelligent handling for tricky cases
## 4) ability to render out corrected BBCode as well as XHTML (NOT YET)
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
## 4) Mostly we work on one-to-one correspondance between
##    'bbtags' and xhtml tags, but we use some tricks to relax
##    the nesting constraints, such as some elements being context 
##     sensitive in the render phase, allowing them to render differently


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
    return html.replace('&', '&amp;').replace('<', '&lt;') \
        .replace('>', '&gt;').replace('"', '&quot;')

###### UTILITY CLASSES ######
class BBTag:
    "Contains info about an allowed tag and tags it can contain"
    def __init__(self, name, allowed_children, implicit_tag, self_closing=False, 
        prohibited_elements = None, discardable = False):
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

_COLORS = ('aqua', 'black', 'blue', 'fuchsia', 'gray', 'green', 'lime', 'maroon', 
    'navy', 'olive', 'purple', 'red', 'silver', 'teal', 'white', 'yellow')
_COLOR_REGEXP = re.compile(r'#[0-9A-F]{6}')
_MEMBER_REGEXP = re.compile(r'^[0-9A-Za-z_]{1,30}$')

# 'text' is a dummy entry for text nodes
_INLINE_TAGS = ('b', 'i', 'color', 'member', 'email', 'url', 
    'br', 'text', 'img', 'softbr', 'emoticon')
_BLOCK_LEVEL_TAGS = ('p', 'quote', 'list', 'pre', 'code', 'div')
_FLOW_TAGS = _INLINE_TAGS + _BLOCK_LEVEL_TAGS
_OTHER_TAGS = ('*',)

_ANCHOR_TAGS = ('member', 'email', 'url')

# Rules, defined so that the output after translation will be 
# XHTML compatible. Other rules are implicit in the parsing routines.
# Note that some bbtags can adapt to their context in the rendering
# phase in order to generate correct XHTML, so have slacker rules than normal
# Also, some tags only exist to make parsing easier, and are
# not intended for use by end user.
_TAGS = (
    BBTag('br', (), 'div', self_closing = True, discardable = True),     # <br/>
    BBTag('softbr', (), 'div', self_closing = True, discardable = True), 
        # <br/>, but can adapt during render
    BBTag('emoticon', ('text',), 'div'),                            
        # <img/>,  but can adapt
    BBTag('b', _INLINE_TAGS, 'div'),                                # <b>
    BBTag('i', _INLINE_TAGS, 'div'),                                # <i>
    BBTag('color', _INLINE_TAGS, 'div'),                            # <span>
    BBTag('member', ('text',), 'div' ),                            # <a>
    BBTag('email', ('text',), 'div'),                              # <a>
    BBTag('url', ('text',), 'div'),                                # <a>
    BBTag('p', _INLINE_TAGS, None),                                 # <p>
    BBTag('div', _FLOW_TAGS, None),                                 # <div>
    BBTag('quote', _BLOCK_LEVEL_TAGS + ('softbr',), 'div'),         # <blockquote>
    BBTag('list', ('*', 'softbr'), None),                          # <ul>
    BBTag('pre', _INLINE_TAGS, None, 
        prohibited_elements = ('img', 'big', 'small', 'sub', 'sup')), 
        # <pre> (only img currently implemented out of those prohibited elements)
    BBTag('code', _INLINE_TAGS, None, 
        prohibited_elements = ('img', 'big', 'small', 'sub', 'sup')), # <pre>
    BBTag('*', _FLOW_TAGS, 'list')
)

# Make a dictionary
_TAGDICT = {}
for t in _TAGS:
    if t.name != 'text':
        _TAGDICT[t.name] = t

# Make list of valid tags
_TAGNAMES = [t.name for t in _TAGS]

# Regexp
_BBTAG_REGEXP = re.compile(r'\[\/?([A-Za-z\*]+)(=[^\]]+)?\]')

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
    'div': 'div'
}

_EMOTICONS = {
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

_EMOTICON_LIST = _EMOTICONS.keys();

###### PARSING CLASSES AND FUNCTIONS ######
class BBNode:
    """Abstract base class for a node of BBcode."""
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        
    def render_children_xhtml(self):
        """Render the child nodes as XHTML"""
        return "".join([child.render_xhtml() for child in self.children])

class BBRootNode(BBNode):
    """Represents a root node"""
    def __init__(self, allow_inline = False):
        BBNode.__init__(self, None)
        self.children = []
        self.allow_inline = allow_inline
    
    def render_xhtml(self):
        """Render the node as XHTML"""
        return self.render_children_xhtml()

    def allows(self, tagname):
        """Returns true if the tag with 'tagname' can be added to this node"""
        if self.allow_inline:
            return tagname in _FLOW_TAGS
        else:
            # Rule for HTML BODY element
            return tagname in _BLOCK_LEVEL_TAGS
    
class BBTextNode(BBNode):
    """A text node, containing only plain text"""
    def __init__(self, parent, text):
        BBNode.__init__(self, parent)
        self.text = text
        
    def render_xhtml(self):
        """Render the node as XHTML"""
        return escape(self.text)

    def allows(self, tagname):
        return False      # text nodes are always leaf nodes

class BBTagNode(BBNode):
    def __init__(self, parent, name, parameter):
        BBNode.__init__(self, parent)
        self.bbtag = _TAGDICT[name]
        self.parameter = parameter
    
    def prohibited(self, tagname):
        """Return True if the element 'tagname' is prohibited by
        this node or any parent nodes"""
        if tagname in self.bbtag.prohibited_elements:
            return True
        else:
            if self.parent is None or not hasattr(self.parent, 'prohibited'):
                return False
            else:
                return self.parent.prohibited(tagname)
    
    def allows(self, tagname):
        """Returns true if the tag with 'tagname' can be added to this node"""
        if tagname in self.bbtag.allowed_children:
            # Check prohibited_elements of this and parent tags
            return not self.prohibited(tagname)
        else:
            return False
        
    def render_xhtml(self):
        """Render the node as XHTML"""
        html_tag = bb2xhtml_map.get(self.bbtag.name, None)        
        if html_tag is None:
            # All tags that need special work
            tagname = self.bbtag.name
            ##############################
            if tagname == 'softbr':
                if self.parent.allows('br'):
                    ret = '<br/>'
                else:
                    ret = '\n'
            ##############################        
            elif tagname == 'emoticon':
                if len(self.children) == 0:
                    return ''
                emoticon = self.children[0].text   # child is always a BBTextNode
                if self.parent.allows('img'):
                    try:
                        imagename = _EMOTICONS.get(emoticon,'')
                    except KeyError:
                        ret = ''
                    else:
                        ret = '<img src="' + EMOTICONS_ROOT + imagename + '" alt="' + \
                            escape(emoticon) + '" />'
                else:
                    ret = emoticon
            ##############################
            elif tagname == 'member':
                if len(self.children) == 0:
                    ret = ''
                else:
                    user = escape(self.children[0].text.strip().replace(" ",""))
                    if len(user) == 0:
                        ret = ''
                    else:
                        ret = get_member_link(user)
            ##############################
            elif tagname == 'url':
                if len(self.children) == 0:
                    ret = ''
                if not self.parameter is None:
                    url = self.parameter.strip()
                else:
                    url = self.children[0].text.strip()
                linktext = self.children[0].text.strip()
                ret = '<a href="' + escape(url) + '">' + escape(linktext) + '</a>'
            ##############################
            elif tagname == 'color':
                if len(self.children) > 0:
                    if self.parameter.lower() in _COLORS or \
                        not _COLOR_REGEXP.match(self.parameter) is None:
                        ret = '<span style="color: ' + self.parameter +  ';">' + \
                            self.render_children_xhtml() + '</span>'
                    else:
                        ret = self.render_children_xhtml()
                else:
                    ret = ''
            ##############################
            elif tagname == 'email':
                if len(self.children) > 0:
                    ret = obfuscate_email(escape(self.children[0].text.strip()))
                else:
                    ret = ''
            ##############################
            elif tagname == 'quote':
                if self.parameter is None:
                    self.parameter = ''
                self.parameter = self.parameter.strip()
                if _MEMBER_REGEXP.match(self.parameter):
                    ret = '<div class="memberquote">' + \
                        get_member_link(self.parameter) + ' said:</div>' + \
                            '<blockquote>' + self.render_children_xhtml() + \
                            '</blockquote>'
                else:
                    ret = '<blockquote>' + self.render_children_xhtml() + \
                        '</blockquote>'
                        
            ##############################
            else:
                raise NotImplementedError('Unknown tag: ' + self.bbtag.name)
        else:
            if self.bbtag.self_closing:
                ret = '<' + html_tag + '>'
            else:
                if len(self.children) > 0:
                    ret = '<' + html_tag + '>' + self.render_children_xhtml() + \
                        '</' + html_tag + '>'
                else:
                    ret = ''
        return ret
        
class BBCodeParser:
    def __init__(self, root_allows_inline = False):
        self.root_node = BBRootNode(root_allows_inline)
        self.current_node = self.root_node
        
    def push_text_node(self, text):
        """Add a text node to the current node"""
        if not self.current_node.allows('text'):
            # e.g. text after [list] but before [*] or after [quote].
            # Only get here if BBRootNode or BBTagNode is current
            if len(text.strip()) == 0:
                # Whitespace, append anyway
                self.current_node.children.append(BBTextNode(self.current_node, text))
            else:
                if self.current_node.allows('div'):
                    self.current_node.children.append(BBTagNode(self.current_node, 'div',''))
                    self.descend()
                else:
                    self.ascend()
                self.push_text_node(text)
        else:
            self.current_node.children.append(BBTextNode(self.current_node, text))
            # text nodes are never open, do don't bother descending
            
    def descend(self):
        """Move to the last child of the current node"""
        self.current_node = self.current_node.children[-1]
        
    def ascend(self):
        """Move to the parent node of the current node"""
        self.current_node = self.current_node.parent
    
    def push_tag_node(self, name, parameter):
        """Add a BBTagNode of name 'name' onto the tree"""
        if not self.current_node.allows(name):
            new_tag = _TAGDICT[name]
            if new_tag.discardable:
                return
            elif (self.current_node == self.root_node or \
                self.current_node.bbtag.name in _BLOCK_LEVEL_TAGS) and\
                not new_tag.implicit_tag is None:
                
                # E.g. [*] inside root, or [*] inside [block]
                # or inline inside root
                # Add an implicit tag if possible
                self.push_tag_node(new_tag.implicit_tag, '')
                self.push_tag_node(name, parameter)
            else:
                # e.g. block level in inline etc. - traverse up the tree
                self.current_node = self.current_node.parent
                self.push_tag_node(name, parameter)
        else:
            node = BBTagNode(self.current_node, name, parameter)
            self.current_node.children.append(node)
            if not node.bbtag.self_closing:
                self.descend()

    def close_tag_node(self, name):
        """Pop the stack back to the first node with the 
        specified tag name, and 'close' that node."""
        temp_node = self.current_node
        while True:
            if temp_node == self.root_node:
                # Give up, effectively discarding the closing tag
                break
            if hasattr(temp_node, 'bbtag'):
                if temp_node.bbtag.name == name:
                    # found it
                    self.current_node = temp_node
                    self.ascend()
                    break
            temp_node = temp_node.parent
            continue
    
    def parse(self, bbcode):
        """Parse the bbcode into a tree of elements"""        
        # Replace newlines with 'soft' brs
        bbcode = bbcode.replace("\n", '[softbr]')
        
        # Replace emoticons with context-sensitive emoticon tags
        for emoticon in _EMOTICON_LIST:
            bbcode = bbcode.replace(emoticon, '[emoticon]' + emoticon + '[/emoticon]')
            
        pos = 0
        while pos < len(bbcode):        
            match = _BBTAG_REGEXP.search(bbcode, pos)
            if not match is None:
                # push all text up to the start of the match
                self.push_text_node(bbcode[pos:match.start()])
                
                # push the tag itself
                tagname = match.groups()[0]
                parameter = match.groups()[1]
                if not parameter is None and len(parameter) > 0:
                    parameter = parameter[1:] # strip the equals
                if tagname in _TAGNAMES:
                    # genuine tag, push it
                    if match.group().startswith('[/'):
                        # closing
                        self.close_tag_node(tagname)
                    else:
                        # opening
                        self.push_tag_node(tagname, parameter)
                pos = match.end()
            else:
                # push all remaining text
                self.push_text_node(bbcode[pos:])
                pos = len(bbcode)
        
    def render_xhtml(self):
        """Render the parsed tree as XHTML"""
        return self.root_node.render_xhtml()

def bb2xhtml(bbcode, root_allows_inline = False):
    "Render bbcode as XHTML"
    parser = BBCodeParser(root_allows_inline)
    parser.parse(bbcode)
    return parser.render_xhtml()
