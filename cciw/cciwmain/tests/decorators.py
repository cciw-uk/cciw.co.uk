from BeautifulSoup import BeautifulSoup
from django.test import TestCase
from client import CciwClient, get_context_var
from forums import CreatePollPage, ADD_POLL_URL
from cciw.cciwmain.decorators import LOGIN_FORM_KEY, LOGIN_FORM_POST_DATA_KEY
import members


# Test our decorators, which are quite complex.
# We use existing views which have the different 
# decorators

def _get_login_post_data(response):
    bs = BeautifulSoup(response.content)
    inp = bs.find(name='input', attrs={'name': LOGIN_FORM_POST_DATA_KEY})
    if inp is None: 
        return inp
    else:
        return inp.attrMap['value']


class MemberRequiredPage(TestCase):
    fixtures = CreatePollPage.fixtures

    def setUp(self):
        self.client = CciwClient()

    def test_get_anonymous(self):
        "Test that we get a login form if we try to view a 'member_required' page"
        r = self.client.get(ADD_POLL_URL)
        self.assert_(LOGIN_FORM_KEY in r.content, "Should get a login form.")

    def test_get_logged_in(self):
        self.client.member_login(members.TEST_POLL_CREATOR_USERNAME, 
                                 members.TEST_POLL_CREATOR_PASSWORD)
        r = self.client.get(ADD_POLL_URL)
        self.assert_(LOGIN_FORM_KEY not in r.content, "Should not get a login form.")

    def test_get_anonymous_produces_final_get(self):
        """Ensure that when we start with a GET request and have to log in, the view ultimately receives a 'GET' request, not a 'POST'"""
        r = self.client.get(ADD_POLL_URL)

        data = self.client.get_member_login_data(members.TEST_POLL_CREATOR_USERNAME, 
                                                 members.TEST_POLL_CREATOR_PASSWORD,
                                                 post_data = _get_login_post_data(r))
        r2 = self.client.post(ADD_POLL_URL, data=data)

        # should be back at orignal page.
        self.assert_(LOGIN_FORM_KEY not in r2.content, "Should not get a login form.")

        # Testing framework nicely preserves the 'request' object for us),
        # but we need the one that the view function actually sees,
        # which has been frigged.  We happen to save it in the context,
        # which is good enough for now.
        orig_request2 = get_context_var(r2.context, 'request')
        self.assertEqual(orig_request2.method, 'GET', "Should reproduce a 'GET' method")

        # Also, no validation should have been done, so context should not
        # have an 'errors' value
        form = get_context_var(r2.context, 'form')
        self.assertEqual(form.errors, {}, "Page should not have done any validation")

    def test_post_produces_final_post(self):
        """Ensure that when we start with a POST request and have to log in, the view ultimately receives a 'POST' with all data"""
        orig_data = {'some':'random_data', 'details':'dont matter'}
        r = self.client.post(ADD_POLL_URL, data=orig_data)

        data = self.client.get_member_login_data(members.TEST_POLL_CREATOR_USERNAME, 
                                                 members.TEST_POLL_CREATOR_PASSWORD,
                                                 post_data = _get_login_post_data(r))
        r2 = self.client.post(ADD_POLL_URL, data=data)

        # should be back at orignal page.
        self.assert_(LOGIN_FORM_KEY not in r2.content, "Should not get a login form.")

        # Testing framework nicely preserves the 'request' object for us),
        # but we need the one that the view function actually sees,
        # which has been frigged.  We happen to save it in the context,
        # which is good enough for now.
        orig_request2 = get_context_var(r2.context, 'request')
        self.assertEqual(orig_request2.method, 'POST', "Should reproduce a 'POST' method")
        self.assertEqual(sorted(orig_request2.POST.items()), 
                         sorted(orig_data.items()), 
                         "Original post data should be present")

        # Also, validation should have been done, so context should 
        # have an 'errors' value
        form = get_context_var(r2.context, 'form')
        self.assertNotEqual(form.errors, {}, "Page should have done some validation")
