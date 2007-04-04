from django.test import client
import cciw.cciwmain.decorators

class CciwClient(client.Client):
    """
    Subclass of the Django Test Client class that knows about
    logging in as a CCIW 'Member' (as well as Django 'User's)
    """

    def member_login(self, membername, password, **extra):
        """
        Does a member login, setting the cookies that are needed.
        """
        # Special knowledge of CCIW code:
        path = '/login/'
        form_data = {
            'user_name': membername,
            'password': password,
            'login': 'Login',
            cciw.cciwmain.decorators.LOGIN_FORM_KEY: '1'
        }
        
        response = self.post(path, data=form_data)
        if response.status_code != 302: # Expect a redirect on successful login
            raise Exception("Failed to log in")
        return response


