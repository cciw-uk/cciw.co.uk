from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.file import SessionStore
from django.test import client


class RequestFactory(client.RequestFactory):
    def request(self, **request):
        retval = super().request(**request)
        retval.user = AnonymousUser()
        retval.session = SessionStore()
        return retval
