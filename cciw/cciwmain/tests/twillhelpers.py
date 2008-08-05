from StringIO import StringIO

import twill
from twill import commands as tc
from django.core.servers.basehttp import AdminMediaHandler
from django.core.handlers.wsgi import WSGIHandler
from django.core.urlresolvers import reverse

def make_twill_url(url):
    return url.replace("http://www.cciw.co.uk/", "http://127.0.0.1:8080/")

BASE = "http://www.cciw.co.uk"
def make_django_url(view, *args, **kwargs):
    return make_twill_url(BASE + reverse(view, args=args, kwargs=kwargs))

def twill_setup():
    app = AdminMediaHandler(WSGIHandler())
    twill.add_wsgi_intercept("127.0.0.1", 8080, lambda: app)

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

    def tearDown(self):
        twill_teardown()

# Twill snippets
# To interactively continue, finish test with this:
#cmd = TwillCommandLoop()
#cmd.cmdloop()
# And make sure that twill.set_output(...) is commented out
