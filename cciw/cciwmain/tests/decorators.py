from django.test import TestCase
from cciw.cciwmain.tests.client import CciwClient
from cciw.cciwmain.tests.forums import CreatePollPage, ADD_POLL_URL
from cciw.cciwmain.decorators import LOGIN_FORM_KEY
from cciw.cciwmain.tests import members


# Test our decorators, which are quite complex.  (Or they were, before
# Simon Willison discovered that the method for propagating POST data
# in insecure, see
# http://www.djangoproject.com/weblog/2008/sep/02/security/ )
#
# We use existing views which have the different decorators.
# Ideally would use Twill for proper testing of this kind of thing.

class MemberRequiredPage(TestCase):
    fixtures = CreatePollPage.fixtures

    def setUp(self):
        self.client = CciwClient()

    def test_get_anonymous(self):
        "Test that we get a login form if we try to view a 'member_required' page"
        r = self.client.get(ADD_POLL_URL)
        self.assertTrue(LOGIN_FORM_KEY in r.content, "Should get a login form.")

    def test_get_logged_in(self):
        self.client.member_login(members.TEST_POLL_CREATOR_USERNAME,
                                 members.TEST_POLL_CREATOR_PASSWORD)
        r = self.client.get(ADD_POLL_URL)
        self.assertTrue(LOGIN_FORM_KEY not in r.content, "Should not get a login form.")

    def test_post_produces_redirect(self):
        """Ensure that when we start with a POST request and have to log in, we get a redirect to the view."""

        data = self.client.get_member_login_data(members.TEST_POLL_CREATOR_USERNAME,
                                                 members.TEST_POLL_CREATOR_PASSWORD)
        r = self.client.post(ADD_POLL_URL, data=data)

        # should be back at orignal page.
        self.assertTrue(LOGIN_FORM_KEY not in r.content, "Should not get a login form.")
        self.assertEqual(r.status_code, 302)

