import xmlrpc.client
# See http://wf.davidsissitka.com/api/reference/
from django.conf import settings


class WebFactionSession(object):
    """
    Class that wraps xmlrpc server calls to always
    provide the webfaction session id as the first
    parameter to method calls
    """
    def __init__(self, server, session_id):
        self.server = server
        self.session_id = session_id

    def __getattr__(self, name):
        def func(*args):
            f = getattr(self.server, name)
            return f(self.session_id, *args)
        return func


def webfaction_session():
    if settings.WEBFACTION_USER is None:
        return None
    server = xmlrpc.client.ServerProxy('https://api.webfaction.com/', allow_none=True)
    session_id, account = server.login(settings.WEBFACTION_USER, settings.WEBFACTION_PASSWORD)
    return WebFactionSession(server, session_id)
