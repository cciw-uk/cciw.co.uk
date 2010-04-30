from StringIO import StringIO

import twill
from twill import commands as tc
from django.core.servers.basehttp import AdminMediaHandler
from django.core.handlers.wsgi import WSGIHandler
from django.core.urlresolvers import reverse
from twill.shell import TwillCommandLoop

def make_twill_url(url):
    url = url.replace("http://www.cciw.co.uk/", "http://127.0.0.1:8080/")
    return url.replace("https://www.cciw.co.uk/", "http://127.0.0.1:8080/")

BASE = "http://www.cciw.co.uk"
def make_django_url(view, *args, **kwargs):
    return make_twill_url(BASE + reverse(view, args=args, kwargs=kwargs))

def twill_setup():
    app = AdminMediaHandler(WSGIHandler())
    twill.add_wsgi_intercept("127.0.0.1", 8080, lambda: app)
    b = twill.get_browser()
    b._browser._factory.is_html = True # make it handle XHTML
    twill.browser = b

def twill_teardown():
    twill.remove_wsgi_intercept('127.0.0.1', 8080)

class TwillMixin(object):
    twill_quiet = True

    def setUp(self):
        twill_setup()
        if self.twill_quiet:
            twill.set_output(StringIO())

    def _twill_login(self, creds):
        tc.go(make_django_url("cciw.officers.views.index"))
        tc.fv(1, 'id_username', creds[0])
        tc.fv(1, 'id_password', creds[1])
        tc.submit()

    def continue_twill(self):
        cmd = TwillCommandLoop()
        cmd.cmdloop()

    def tearDown(self):
        twill_teardown()

# Twill snippets
# To interactively continue, finish test with this:
#   self.continue_twill()
# And add
#   twill_quiet = False
# to the class
