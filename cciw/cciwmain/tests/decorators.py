from client import CciwClient
from forums import CreatePollPage, ADD_POLL_URL
from cciw.cciwmain.decorators import LOGIN_FORM_KEY

# Test our decorators, which are quite complex.
# We use existing views which have the different 
# decorators

class MemberRequiredPage(TestCase):
    fixtures = CreatePollPage.fixtures

    def setUp(self):
        self.client = CciwClient()

    def testGetAnonymous(self):
        "Test that we get a login form if we try to view a 'member_required' page"
        r = self.client.get(ADD_POLL_URL)
        self.assert_(LOGIN_FORM_KEY in r.content, "Should get a login form.")
