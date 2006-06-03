#####################################################################
##    Copyright (c) 2005-2006, Luke Plant 
##    All rights reserved.
##    E-mail: <L.Plant.98@cantab.net>
##    Web: http://lukeplant.me.uk/
##    
##    Redistribution and use in source and binary forms, with or without
##    modification, are permitted provided that the following conditions are
##    met:
##    
##        * Redistributions of source code must retain the above copyright
##          notice, this list of conditions and the following disclaimer.
##    
##        * Redistributions in binary form must reproduce the above
##          copyright notice, this list of conditions and the following
##          disclaimer in the documentation and/or other materials provided
##          with the distribution.
##    
##        * The name of Luke Plant may not be used to endorse or promote 
##          products derived from this software without specific prior 
##          written permission.
##    
##    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
##    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
##    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
##    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
##    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
##    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
##    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
##    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
##    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
##    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
##    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

##########################################################################
## Module to convert BBCode to XHTML, featuring:
##
## 1) full XHTML compliance, including prohibited elements
## 2) intelligent handling/preserving of whitespace
## 3) emoticons, with intelligent handling for tricky cases
## 4) ability to render out corrected BBCode as well as XHTML
## 5) XHTML outputed can be inserted into <body>, <div>, <td>
##    and any other elements that allow block level tags
## 6) Excellent 'do what I mean' handling of bbcode input.
##
## IMPLEMENTATION NOTES
## 
## 1) I have implemented what I needed and used for my own needs,
##    which isn't necessarily 'standard' bbcode, if such a thing exists
## 2) There are some definitely web site specific extensions
##    e.g. [email], [member], the rendering of [quote=person]
## 3) 'Missing' tags - [img] - but should be easy to add
## 4) Mostly it works on one-to-one correspondance between
##    'bbtags' and xhtml tags, but with some added constraints to force
##    extra elements to be inserted to comply with XHTML, and
##    use some tricks to relax the nesting constraints, such 
##    as some elements being context sensitive in the render phase

import re
import urllib

#### CCIW specific imports #####
from cciw.cciwmain.utils import get_member_link, obfuscate_email
from django.conf import settings
EMOTICONS_ROOT = settings.CCIW_MEDIA_URL + 'images/emoticons/'
ESV_BROWSE_URL = settings.ESV_BROWSE_URL

##### UTILITY FUNCTIONS #####
def escape(html):
    "Returns the given HTML with ampersands, quotes and carets encoded"
    if not isinstance(html, basestring):
        html = str(html)
    return html.replace('&', '&amp;').replace('<', '&lt;') \
        .replace('>', '&gt;').replace('"', '&quot;')
        
###### BBCODE ELEMENT DEFINITIONS ######
# The 'Tag' classes are used as singletons,
# created in the 'rules' section.
class BBTag:
    """Represents an allowed tag with its name and meta data."""
    def __init__(self, name, allowed_children, implicit_tag, self_closing=False, 
        prohibited_elements = None, discardable = False):
        """Creates a new BBTag.
        - name is the text appears in square brackets e.g. for [b], name = 'b'
        - allowed_children is a list of the names of tags that can be added to this element
        - implicit_tag is a tag that can automatically be added before this one 
          if necessary to allow it to be added.
        - self_closing means the element never has child elements
        - prohibited_elements is a list of elements that can never be 
          descendent elements of this one
        - discardable = True indicates that the tag can be discarded if 
          it can't be added at the current point in the tree.
        """
        
        if prohibited_elements is None:
            self.prohibited_elements = ()
        else:
            self.prohibited_elements = prohibited_elements
        self.self_closing = self_closing
        self.name = name
        self.implicit_tag = implicit_tag
        self.allowed_children = allowed_children
        self.discardable = discardable
        
    def render_node_xhtml(self, node):
        """
        Renders a node of this BBTag as HTML.
        node is the node to render.
        """
        raise NotImplementedException()
    
    def render_node_bbcode(self, node):
        opening = self.name # opening tag
        if node.parameter:
            opening += "=" + node.parameter
        if self.self_closing:
            return '[%s]' % opening
        else:
            return '[%s]%s[/%s]' % \
                (opening, node.render_children_bbcode(), self.name)

## Subclasses that follow override the render_node_xhtml 
## or render_node_bbcode method
        
class HtmlEquivTag(BBTag):
    """
    A BBTag that is a direct equivalent of an HTML tag, and can render itself.
    """
    def __init__(self, *args, **kwargs):
        self.html_equiv = kwargs.pop('html_equiv')
        self.attributes = kwargs.pop('attributes', None)
        BBTag.__init__(self, *args, **kwargs)
    
    def render_node_xhtml(self, node):
        opening = self.html_equiv
        if self.attributes:
            # Add any attributes
            opening += ' ' + ' '.join(['%s="%s"' % (k, escape(v)) 
                                        for k, v in self.attributes.items()])
        if self.self_closing:
            ret = '<' + opening + '/>'
        else:
            if len(node.children) > 0:
                ret = '<' + opening + '>' + node.render_children_xhtml() + \
                    '</' + self.html_equiv + '>'
            else:
                ret = ''
        return ret

class LiTag(HtmlEquivTag):
    """
    An <li> tag.
    """
    def __init__(self, *args, **kwargs):
        kwargs['html_equiv'] = 'li'
        HtmlEquivTag.__init__(self, *args, **kwargs)

    def render_node_bbcode(self, node):
        # Don't render closing [/*]
        return '[%s]%s' % \
                (self.name, node.render_children_bbcode())

class SoftBrTag(BBTag):
    """A tag representing an optional <br>"""
    def render_node_xhtml(self, node):
        if node.parent.allows('br'):
            return '<br/>'
        else:
            return '\n'
            
    def render_node_bbcode(self, node):
        return '\n'

class Emoticon(BBTag):
    def render_node_xhtml(self, node):
        if len(node.children) == 0:
            return ''
        emoticon = node.children[0].text   # child is always a BBTextNode
        if node.parent.allows('img'):
            imagename = _EMOTICONS.get(emoticon,'')
            if imagename == '':
                return ''
            else:
                return '<img src="' + EMOTICONS_ROOT + imagename + '" alt="' + \
                    escape(emoticon) + '" />'
        else:
            return emoticon
            
    def render_node_bbcode(self, node):
        return node.children[0].text

class ColorTag(BBTag):
    def render_node_xhtml(self, node):
        if len(node.children) > 0:
            if node.parameter.lower() in _COLORS or \
                _COLOR_REGEXP.match(node.parameter) is not None:
                return '<span style="color: ' + node.parameter +  ';">' + \
                    node.render_children_xhtml() + '</span>'
            else:
                return node.render_children_xhtml()
        else:
            return ''

class MemberTag(BBTag):
    def render_node_xhtml(self, node):
        if len(node.children) == 0:
            return ''
        else:
            member_name = escape(node.children[0].text.strip().replace(" ", ""))
            if len(member_name) == 0:
                return ''
            else:
                return get_member_link(member_name)

class EmailTag(BBTag):
    def render_node_xhtml(self, node):
        if len(node.children) > 0:
            return obfuscate_email(escape(node.children[0].text.strip()))
        else:
            return ''
            
class UrlTag(BBTag):
    def render_node_xhtml(self, node):
        if len(node.children) == 0:
            return ''
        if not node.parameter is None:
            url = node.parameter.strip()
        else:
            url = node.children[0].text.strip()
        linktext = node.children[0].text.strip()
        if len(url) == 0:
            return ''
        else:
            return '<a href="' + escape(url) + '">' + escape(linktext) + '</a>'

class QuoteTag(BBTag):
    def render_node_xhtml(self, node):
        if node.parameter is None:
            node.parameter = ''
        else:
            node.parameter = node.parameter.strip()
        if _MEMBER_REGEXP.match(node.parameter):
            return '<div class="memberquote">' + \
                get_member_link(node.parameter) + ' said:</div>' + \
                    '<blockquote>' + node.render_children_xhtml() + \
                    '</blockquote>'
        else:
            return '<blockquote>' + node.render_children_xhtml() + \
                '</blockquote>'

class BibleTag(BBTag):
    def render_node_xhtml(self, node):
        output = ''
        if node.parameter is not None:
            url = ESV_BROWSE_URL + "?" + urllib.urlencode({'q':node.parameter})
            output += '<div class="biblequote"><a href="%s" title="Browse %s in the ESV">%s:</a></div>' % \
                (escape(url), escape(node.parameter), escape(node.parameter))
        output += '<blockquote class="bible">' + node.render_children_xhtml() + '</blockquote>'
        return ''.join(output)

###### DATA ######

_COLORS = ('aqua', 'black', 'blue', 'fuchsia', 'gray', 'green', 'lime', 'maroon', 
    'navy', 'olive', 'purple', 'red', 'silver', 'teal', 'white', 'yellow')
_COLOR_REGEXP = re.compile(r'#[0-9A-F]{6}')
_MEMBER_REGEXP = re.compile(r'^[0-9A-Za-z_]{1,30}$')
_BBTAG_REGEXP = re.compile(r'\[\[?\/?([A-Za-z\*]+)(=[^\]]+)?\]?\]')

# 'text' is a dummy entry for text nodes
_INLINE_TAGS = (
    'b', 'i', 'color', 'member', 'email', 'url', 
    'br', 'text', 'img', 'softbr', 'emoticon'
)
_BLOCK_LEVEL_TAGS = ('p', 'quote', 'list', 'pre', 'code', 'div', 'bible')
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
    #           name          allowed_children   implicit_tag
    # <br/>
    HtmlEquivTag('br',         (),             'div', 
        self_closing=True, discardable=True, html_equiv='br'),
    
    # <br/>, but can adapt during render
    SoftBrTag   ('softbr',     (),             'div', 
        self_closing=True, discardable=True),
    
    # <img/>,  but can adapt
    Emoticon    ('emoticon',   ('text',),      'div'),
    
    # <b>
    HtmlEquivTag('b',          _INLINE_TAGS,   'div',
        html_equiv='b'),
    
    # <i>
    HtmlEquivTag('i',          _INLINE_TAGS,   'div',
        html_equiv='i'),
    
    # <span>
    ColorTag    ('color',      _INLINE_TAGS,   'div'),
    
    # <a>
    MemberTag   ('member',     ('text',),      'div' ),
    
    # <a>
    EmailTag    ('email',      ('text',),      'div'),
    
    # <a>
    UrlTag      ('url',        ('text',),      'div'),
    
    # <p>
    HtmlEquivTag('p',          _INLINE_TAGS,   None,
        html_equiv='p'),
    
    # <div>
    HtmlEquivTag('div',        _FLOW_TAGS,     None,
        html_equiv='div'),
    
    # <blockquote>
    QuoteTag    ('quote',      _BLOCK_LEVEL_TAGS + ('softbr',), 'div'),
    
    # <blockquote>
    BibleTag    ('bible',      _BLOCK_LEVEL_TAGS + ('softbr',), 'div'),
    
    # <ul>
    HtmlEquivTag('list',       ('*', 'softbr'),None,
        html_equiv='ul'),
    
    # <pre> (only img currently needed out of the prohibited elements)
    HtmlEquivTag('pre',        _INLINE_TAGS,   None, 
        prohibited_elements=('img', 'big', 'small', 'sub', 'sup'),
        html_equiv='pre'), 
    
    # <pre class="code">
    HtmlEquivTag('code',       _INLINE_TAGS,   None, 
        prohibited_elements = ('img', 'big', 'small', 'sub', 'sup'),
        html_equiv='pre', attributes={'class':'code'}),
        
    # <li>
    LiTag('*',                 _FLOW_TAGS,     'list',)
)

# Make a dictionary
_TAGDICT = {}
for t in _TAGS:
    if t.name != 'text':
        _TAGDICT[t.name] = t

# Make list of valid tags
_TAGNAMES = [t.name for t in _TAGS]

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

    def render_children_bbcode(self):
        """Render the child nodes as BBCode"""
        return "".join([child.render_bbcode() for child in self.children])

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

    def render_bbcode(self):
        """Render the node as correct BBCode"""
        return self.render_children_bbcode()

class BBTextNode(BBNode):
    """A text node, containing only plain text"""
    def __init__(self, parent, text):
        BBNode.__init__(self, parent)
        self.text = text
        
    def render_xhtml(self):
        """Render the node as XHTML"""
        return escape(self.text)

    def render_bbcode(self):
        return self.text

    def allows(self, tagname):
        return False      # text nodes are always leaf nodes

class BBEscapedTextNode(BBTextNode):
    """Node used for text that uses the escaping mechanism: [[foo]].
    Only needed for rendering bbcode."""
    def render_bbcode(self):
        return '[' + self.text + ']'

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
        return self.bbtag.render_node_xhtml(self)

    def render_bbcode(self):
        return self.bbtag.render_node_bbcode(self)

class BBCodeParser:
    def __init__(self, root_allows_inline = False):
        self.root_allows_inline = root_allows_inline

    def push_text_node(self, text, escaped=False):
        """Add a text node to the current node"""
        # escaped=True for text that has been wrapped in extra []
        # to stop interpretation as bbcode
        
        if escaped:
            text_class = BBEscapedTextNode
        else:
            text_class = BBTextNode

        if not self.current_node.allows('text'):
            # e.g. text after [list] but before [*] or after [quote].
            # Only get here if BBRootNode or BBTagNode is current
            if len(text.strip()) == 0:
                # Whitespace, append anyway
                self.current_node.children.append(text_class(self.current_node, text))
            else:
                if self.current_node.allows('div'):
                    self.current_node.children.append(BBTagNode(self.current_node, 'div',''))
                    self.descend()
                else:
                    self.ascend()
                self.push_text_node(text)
        else:
            self.current_node.children.append(text_class(self.current_node, text))
            # text nodes are never open, do don't bother descending

    def descend(self):
        """Move to the last child of the current node"""
        self.current_node = self.current_node.children[-1]

    def ascend(self):
        """Move to the parent node of the current node"""
        # This usually closes the node, since parsing
        # will add nodes to the end of self.children
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
                
                # E.g. [*] inside root, or [*] inside [quote]
                # or inline inside root
                # Add an implicit tag if possible
                self.push_tag_node(new_tag.implicit_tag, '')
                self.push_tag_node(name, parameter)
            else:
                # e.g. block level in inline etc. - traverse up the tree
                self.current_node = self.current_node.parent
                self.push_tag_node(name, parameter) # recursive call
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

    def _prepare(self, bbcode):
        # Replace newlines with 'soft' brs
        bbcode = bbcode.replace("\n", '[softbr]')
        
        # Replace emoticons with context-sensitive emoticon tags
        for emoticon in _EMOTICON_LIST:
            bbcode = bbcode.replace(emoticon, 
                '[emoticon]' + emoticon + '[/emoticon]')
        return bbcode

    def parse(self, bbcode):
        """Parse the bbcode into a tree of elements"""        
        self.root_node = BBRootNode(self.root_allows_inline)
        self.current_node = self.root_node
        bbcode = self._prepare(bbcode)
        pos = 0
        while pos < len(bbcode):
            match = _BBTAG_REGEXP.search(bbcode, pos)
            if not match is None:
                # push all text up to the start of the match
                self.push_text_node(bbcode[pos:match.start()])
                
                # push the tag itself
                tagname = match.groups()[0]
                parameter = match.groups()[1]
                wholematch = match.group()
                if wholematch.startswith('[[') and wholematch.endswith(']]'):
                    # escaping mechanism
                    self.push_text_node(wholematch[1:-1], escaped=True)
                else:
                    if not parameter is None and len(parameter) > 0:
                        parameter = parameter[1:] # strip the equals
                    if tagname in _TAGNAMES:
                        # genuine tag
                        if wholematch.startswith('[['):
                            # in case of "[[tag]blah":
                            self.push_text_node('[')
                        # push it
                        if wholematch.startswith('[/'):
                            # closing
                            self.close_tag_node(tagname)
                        else:
                            # opening
                            self.push_tag_node(tagname, parameter)
                        if wholematch.endswith(']]'):
                            # in case of "[tag]]":
                            self.push_text_node(']')
                    else:
                        # non-genuine tag, treat as literal
                        self.push_text_node(wholematch)
                pos = match.end()
            else:
                # push all remaining text
                self.push_text_node(bbcode[pos:])
                pos = len(bbcode)
        
    def render_xhtml(self):
        """Render the parsed tree as XHTML"""
        return self.root_node.render_xhtml()
        
    def render_bbcode(self):
        """Render the parsed tree as corrected BBCode"""
        return self.root_node.render_bbcode()

def bb2xhtml(bbcode, root_allows_inline = False):
    "Render bbcode as XHTML"
    parser = BBCodeParser(root_allows_inline)
    parser.parse(bbcode)
    return parser.render_xhtml()
    
def correct(bbcode):
    "Renders corrected bbcode"
    parser = BBCodeParser(True)
    parser.parse(bbcode)
    return parser.render_bbcode()
