import bbcode
import unittest

import sys
import os



tests = (
	('<test&',
		'<p>&lt;test&amp;</p>'),
	('[b]Incorrectly [i]nested tags[/b] must be dealt with[/i]', 
		'<p><b>Incorrectly <i>nested tags</i></b> must be dealt with</p>'),
	('[quote]this must be in a para[/quote]', 
		'<blockquote><p>this must be in a para</p></blockquote>'),
	('Newlines\nconverted\n\nto brs', 
		'<p>Newlines<br/>converted<br/><br/>to brs</p>'),
	('[list][br][*]brs discarded when illegal', 
		'<ul><li>brs discarded when illegal</li></ul>'),
	('[list]\n[*]Newlines not discarded, or converted when brs would be illegal', 
		'<ul>\n<li>Newlines not discarded, or converted when brs would be illegal</li></ul>'),
	('[quote]\nNewlines not discarded at beginning of quote', 
		'<blockquote>\n<p>Newlines not discarded at beginning of quote</p></blockquote>'),
	('[list]Text in root of list tag is moved outside[*]and put in a paragraph[/list]',
		'<p>Text in root of list tag is moved outside</p><ul><li>and put in a paragraph</li></ul>'),
	(':-) :bosh:',
		'<p><img src="' + bbcode.EMOTICONS_ROOT + 'smile.gif" alt=":-)" /> <img src="' + bbcode.EMOTICONS_ROOT + 'mallet1.gif" alt=":bosh:" /></p>' ),
	('[code]:-) :bosh:[/code]',
		'<pre>:-) :bosh:</pre>'),	
	('[url]/foo/?a=1&b=2[/url]',
		'<p><a href="/foo/?a=1&amp;b=2">/foo/?a=1&amp;b=2</a></p>'),
	('[url=/foo/?a=1&b=2]bar[/url]',
		'<p><a href="/foo/?a=1&amp;b=2">bar</a></p>'),
	('[member]Joey[/member]',
		'<p><a href="/members/Joey/">Joey</a></p>'),
	('[member]illegal " name[/member]',
		'<p><a href="/members/illegal&quot;name/">illegal&quot;name</a></p>'),
	('ok, ill go first...[br][br][color=red]b[color=orange]e[color=yellow]a[color=green]u[color=blue]t[color=purple]i[color=magenta]f[color=pink]u[color=red]l[/color]  :-) [color=black](the surroundings and everyone in it)',
		'<p>ok, ill go first...<br/><br/><span style="color: red;">be<span style="color: yellow;">a<span style="color: green;">u<span style="color: blue;">t<span style="color: purple;">ifu<span style="color: red;">l</span>  <img src="http://cciw_django_local/media/images/emoticons/smile.gif" alt=":-)" /> <span style="color: black;">(the surroundings and everyone in it)</span></span></span></span></span></span></p>'),
)

class TestBBCodeParser(unittest.TestCase):
	
	def testRenderXhtml(self):
		for bb, xhtml in tests:
			result = bbcode.bb2xhtml(bb)
			self.assertEqual(xhtml, result, "\n----BBcode:\n " +bb + "\n----Rendered as:\n" + result + 
				"\n---- instead of \n" + xhtml)
				
	def testRenderAllPosts(self):
		from django.models.forums import posts
		from django.models.members import messages
		from cciw.apps.cciw.utils import validateXML
		f = open('/home/luke/all_cciw_posts.html', 'w')
		f.write("""
		<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<title>foo</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head>
<body>
""")
		f.writelines(["<!-- " + p.message.replace("-", "=") + " -->\n" + bbcode.bb2xhtml(p.message)+"\n\n" for p in posts.get_list()])
		f.writelines(["<!-- " + m.text.replace("-", "=") + " -->\n" + bbcode.bb2xhtml(m.text)+"\n\n" for m in messages.get_list()])
		f.write("</body></html>")
		f.close()		
		
		self.assertTrue(validateXML('/home/luke/all_cciw_posts.html'))


if __name__ == '__main__':
	sys.path = sys.path + ['/home/httpd/www.cciw.co.uk/django/','/home/httpd/www.cciw.co.uk/django_src/']
	os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings.main'
	
	unittest.main()

