
import twill
from django.core.servers.basehttp import AdminMediaHandler
from django.core.handlers.wsgi import WSGIHandler

def make_twill_url(url):
    return url.replace("http://www.cciw.co.uk/", "http://127.0.0.1:8080/")

def twill_setup():
    app = AdminMediaHandler(WSGIHandler())
    twill.add_wsgi_intercept("127.0.0.1", 8080, lambda: app)

def twill_teardown():
    twill.remove_wsgi_intercept('127.0.0.1', 8080)

class TwillMixin(object):
    def setUp(self):
        twill_setup()

    def tearDown(self):
        twill_teardown()

# Twill snippets 
# To interactively continue, finish test with this:
#cmd = TwillCommandLoop()
#cmd.cmdloop()
# And make sure that twill.set_output(...) is commented out
