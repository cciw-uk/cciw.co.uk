import unittest
import sys
import os

# set up environment variables for testing (needed by imports in bbcode)
sys.path = sys.path + ['/home/httpd/www.cciw.co.uk/django/','/home/httpd/www.cciw.co.uk/django_src/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'

import bbcode
from cciw.apps.cciw.utils import get_member_link   


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
    ('[list]Text in root of list tag is moved outside[*]and put in a div[/list]',
        '<div>Text in root of list tag is moved outside<ul><li>and put in a div</li></ul></div>'),
    (':-) :bosh:',
        '<div><img src="' + bbcode.EMOTICONS_ROOT + 'smile.gif" alt=":-)" /> <img src="' + bbcode.EMOTICONS_ROOT + 'mallet1.gif" alt=":bosh:" /></div>' ),
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
        '<div><a title="Information about user \'illegal&quot;name\'" href="/members/illegal&quot;name/">illegal&quot;name</a></div>'),
    # Real example from typical user who doesn't bother with closing tags:
    ('ok, ill go first...[br][br][color=red]b[color=orange]e[color=yellow]a[color=green]u[color=blue]t[color=purple]i[color=magenta]f[color=pink]u[color=red]l[/color]  :-) [color=black](the surroundings and everyone in it)',
        '<div>ok, ill go first...<br/><br/><span style="color: red;">be<span style="color: yellow;">a<span style="color: green;">u<span style="color: blue;">t<span style="color: purple;">ifu<span style="color: red;">l</span>  <img src="http://cciw_django_local/media/images/emoticons/smile.gif" alt=":-)" /> <span style="color: black;">(the surroundings and everyone in it)</span></span></span></span></span></span></div>'),
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
    ('[[b]] [[/b]] [[quote=foo]] [[[b]]]',
        '<div>[b] [/b] [quote=foo] [[b]]</div>'),
    # text that is accidentally similar to escaping:
    ('[[b]Just some bold text in square brackets[/b]]',
        '<div>[<b>Just some bold text in square brackets</b>]</div>'),
    
    # non-existant tags come through as literals
    ('[nonexistanttag]',    
        '<div>[nonexistanttag]</div>'),
)

class TestBBCodeParser(unittest.TestCase):
    def test_render_xhtml(self):
        for bb, xhtml in tests:
            result = bbcode.bb2xhtml(bb)
            self.assertEqual(xhtml, result, "\n----BBcode:\n " +bb + "\n----Rendered as:\n" + result + 
                "\n---- instead of \n" + xhtml)

    def test_correct(self):
        # After a single 'correction', doing correct()
        # should be an identity transformation in all cases
        for bb, xhtml in tests:
            corrected_bb = bbcode.correct(bb)
            twice_corrected_bb = bbcode.correct(corrected_bb)
            self.assertEqual(corrected_bb, twice_corrected_bb, 
                "\n----BBcode:\n " +bb + "\n----Once corrected\n" + corrected_bb + 
                "\n----Twice corrected:\n" + twice_corrected_bb)

    def test_correct_preserves_whitespace(self):
        # These examples are correct bbcode with whitespace
        # in various places, and 'correct' shouldn't mess with our whitespace!
        bb = " Hello\nHow\nAre \n\nYou "
        self.assertEqual(bb, bbcode.correct(bb))
        bb = "[list]\n  [*]Item1[/*]\n[*]Item2 [/*]\n[/list]\n"
        self.assertEqual(bb, bbcode.correct(bb))

if __name__ == '__main__':
    unittest.main()

