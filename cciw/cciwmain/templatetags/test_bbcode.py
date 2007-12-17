# # -*- coding: utf-8 -*-
import sys
import os

import bbcode
from cciw.cciwmain.utils import get_member_link   


tests = (
    ('<test&',
        '<div>&lt;test&amp;</div>'),
    ('[b]Incorrectly [i]nested tags[/b] must be dealt with[/i]', 
        '<div><b>Incorrectly <i>nested tags</i></b> must be dealt with</div>'),
    ('[quote]this must be in a div[/quote]', 
        '<blockquote><div>this must be in a div</div></blockquote>'),
    ('Newlines\nconverted\n\nto brs', 
        '<div>Newlines<br/>converted<br/><br/>to brs</div>'),
    ('[list][br][*]brs discarded when illegal', 
        '<ul><li>brs discarded when illegal</li></ul>'),
    ('[list]\n[*]Newlines not discarded, or converted when brs would be illegal', 
        '<ul>\n<li>Newlines not discarded, or converted when brs would be illegal</li></ul>'),
    ('[quote]\nNewlines not discarded at beginning of quote', 
        '<blockquote>\n<div>Newlines not discarded at beginning of quote</div></blockquote>'),
    (u'[list]Text in root of list tag is moved outside[*]and put in a div é[/list]',
        u'<div>Text in root of list tag is moved outside<ul><li>and put in a div é</li></ul></div>'),
    (':-) :bosh:',
        '<div><img src="' + bbcode.EMOTICONS_ROOT + 'smile.gif" alt=":-)" /> <img src="' + bbcode.EMOTICONS_ROOT + 'mallet1.gif" alt=":bosh:" /></div>' ),
    ('0:-)',
        '<div><img src="' + bbcode.EMOTICONS_ROOT + 'angel.gif" alt="0:-)" /></div>' ),
    ('[code]:-) :bosh:[/code]',
        '<pre class="code">:-) :bosh:</pre>'),    
    ('[url]/foo/?a=1&b=2[/url]',
        '<div><a href="/foo/?a=1&amp;b=2">/foo/?a=1&amp;b=2</a></div>'),
    ('[url=/foo/?a=1&b=2]bar[/url]',
        '<div><a href="/foo/?a=1&amp;b=2">bar</a></div>'),
    # empty url
    ('[url][/url]',
        '<div></div>'),
    ('[member]Joey[/member]',
        '<div>' + get_member_link('Joey') + '</div>'),
    ('[member]illegal " name[/member]',
        '<div><a title="Information about user \'illegal&quot;name\'" href="">illegal&quot;name</a></div>'),
    # Real example from typical user who doesn't bother with closing tags:
    ('ok, ill go first...[br][br][color=red]b[color=orange]e[color=yellow]a[color=green]u[color=blue]t[color=purple]i[color=magenta]f[color=pink]u[color=red]l[/color]  :-) [color=black](the surroundings and everyone in it)',
        '<div>ok, ill go first...<br/><br/><span style="color: red;">be<span style="color: yellow;">a<span style="color: green;">u<span style="color: blue;">t<span style="color: purple;">ifu<span style="color: red;">l</span>  <img src="' + bbcode.EMOTICONS_ROOT + 'smile.gif" alt=":-)" /> <span style="color: black;">(the surroundings and everyone in it)</span></span></span></span></span></span></div>'),
    ('[quote= foo1_23 ]Blah[/quote]',
        '<div class="memberquote">' + get_member_link('foo1_23') + ' said:</div><blockquote><div>Blah</div></blockquote>'),
    ('[quote=foo123%]Blah[/quote]',
        '<blockquote><div>Blah</div></blockquote>'),
    # Trim empty emoticons
    ('[emoticon][/emoticon]',
        '<div></div>'),
    # And attempts to get other images (just tests an assumption in code)
    ('[emoticon]hello[/emoticon]',
        '<div></div>'),
    # escaping:
    (u'[[b]] [[/b]] [[quote=fooé]] [[[b]]]',
        u'<div>[b] [/b] [quote=fooé] [[b]]</div>'),
    # text that is accidentally similar to escaping:
    ('[[b]Just some bold text in square brackets[/b]]',
        '<div>[<b>Just some bold text in square brackets</b>]</div>'),
    
    # non-existant tags come through as literals
    (u'[nonéxistanttag]',    
        u'<div>[nonéxistanttag]</div>'),
    # empty string should return nothing
    ('',
        ''),
    # Bible:
    ('[bible]test',
        '<blockquote class="bible"><div>test</div></blockquote>'),
    ('[bible=John 3:16]For God so loved the world[/bible]',
        '<div class="biblequote"><a href="http://www.gnpcb.org/esv/search/?q=John+3%3A16" ' + \
        'title="Browse John 3:16 in the ESV">John 3:16:</a></div><blockquote class="bible"><div>For God so loved the world</div></blockquote>'),
)

def check_xhtml(bb, xhtml):
    assert bbcode.bb2xhtml(bb) == xhtml
    
def test_render_xhtml():
    for bb, xhtml in tests:
        yield check_xhtml, bb, xhtml

def check_correction(bb):
    "utility function for generating tests"
    corrected_bb = bbcode.correct(bb)
    twice_corrected_bb = bbcode.correct(corrected_bb)
    assert corrected_bb == twice_corrected_bb

def test_correct():
    # After a single 'correction', doing correct()
    # should be an identity transformation in all cases
    for bb, xhtml in tests:
        yield check_correction, bb

def test_unicode():
    # Should always return unicode objects
    for bb, xhtml in tests:
        yield check_unicode, bb

def check_unicode(bb):
    assert type(bbcode.bb2xhtml(bb)) is unicode

def test_correct_preserves_whitespace():
    # These examples are correct bbcode with whitespace
    # in various places, and 'correct' shouldn't mess with our whitespace!
    bb = " Hello\nHow\nAre \n\nYou "
    assert bb == bbcode.correct(bb)
    bb = "[list]\n  [*]Item1\n[*]Item2 \n[/list]\n"
    assert bb == bbcode.correct(bb)

def test_correct_eliminates_div():
    # Check we don't get '[div]' in corrected output
    bb = "[quote]test[/quote]"
    assert bb == bbcode.correct(bb)

def do_all():
    for bb, html in tests:
        bbcode.bb2xhtml(bb)
