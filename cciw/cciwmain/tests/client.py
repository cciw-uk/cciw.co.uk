from django.test import client
import cciw.cciwmain.decorators

class CciwClient(client.Client):
    """
    Subclass of the Django Test Client class that knows about
    logging in as a CCIW 'Member' (as well as Django 'User's)
    """

    @staticmethod
    def get_member_login_data(membername, password, post_data=None):
        # Special knowledge of CCIW code:
        form_data = {
            'user_name': membername,
            'password': password,
            'login': 'Login',
            cciw.cciwmain.decorators.LOGIN_FORM_KEY: '1'
        }
        if post_data is not None:
            form_data[cciw.cciwmain.decorators.LOGIN_FORM_POST_DATA_KEY] = post_data
        
        return form_data

    def member_login(self, membername, password, **extra):
        """
        Does a member login, setting the cookies that are needed.
        """
        path = '/login/'
        
        response = self.post(path, data=self.get_member_login_data(membername, password))
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

