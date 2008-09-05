from django.test import client
import cciw.cciwmain.decorators

LOGIN_URL = '/login/'

class CciwClient(client.Client):
    """
    Subclass of the Django Test Client class that knows about
    logging in as a CCIW 'Member' (as well as Django 'User's)
    """

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
        if response.status_code != 302: # Expect a redirect on successful login
            raise Exception("Failed to log in")
        return response


    def member_logout(self):
        self.cookies.clear()

def get_context_var(context_list, var, default=None):
    """Returns a context variable from the Django response.context object"""
    if isinstance(context_list, list):
        for d in reversed(context_list):
            if d.has_key(var):
                return d[var]
    else:
        if context_list.has_key(var):
            return context_list[var]
    return default

