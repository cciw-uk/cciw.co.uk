from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.file import SessionStore
from django.test import client

import cciw.cciwmain.decorators

LOGIN_URL = '/login/'


class CciwClient(client.Client):
    """
    Subclass of the Django Test Client class that knows about
    logging in as a CCIW 'Member'.
    """
    # Use the superclass's login() method for officer login (contrib.auth.User)

    @staticmethod
    def get_member_login_data(membername, password):
        # Special knowledge of CCIW code:
        form_data = {
            'user_name': membername,
            'password': password,
            'login': 'Login',
            cciw.cciwmain.decorators.LOGIN_FORM_KEY: '1'
        }

        return form_data

    def member_login(self, membername, password):
        """
        Does a member login, setting the cookies that are needed.
        """
        response = self.post(LOGIN_URL, data=self.get_member_login_data(membername, password))
        if response.status_code != 302:  # Expect a redirect on successful login
            raise Exception("Failed to log in")
        return response

    def member_logout(self):
        self.cookies.clear()


class RequestFactory(client.RequestFactory):

    def request(self, **request):
        retval = super(RequestFactory, self).request(**request)
        retval.user = AnonymousUser()
        retval.session = SessionStore()
        return retval
