from django.test import client, TestCase
from cciw.cciwmain.models import Member
import cciw.cciwmain.views.members

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


TEST_MEMBER = 'test_member_1'
TEST_MEMBER_PASSWORD = 'password'

class SimpleTest(TestCase):
    fixtures=['basic.yaml','test_members.yaml']
    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER, TEST_MEMBER_PASSWORD)

    def test_set_prefs(self):
        response = self.client.get('/memberadmin/preferences/')
        self.failUnlessEqual(response.status_code, 200)
        self.assert_("Edit your preferences below" in response.content)
