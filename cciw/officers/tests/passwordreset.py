from django.test import TestCase
from django.core import mail
from references import OFFICER
import re
from django.contrib.auth.models import User
from cciw.cciwmain.tests.members import url_to_path_and_query
import cciw.officers.views

class PasswordResetTest(TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml']

    def test_email_not_found(self):
        response = self.client.get('/admin/password_reset/')
        self.assertEquals(response.status_code, 200)
        response = self.client.post('/admin/password_reset/', {'email': 'not_a_real_email@email.com'})
        self.assertContains(response, "That e-mail address doesn't have an associated user account")
        self.assertEquals(len(mail.outbox), 0)

    def test_email_found(self):
        response = self.client.post('/admin/password_reset/', {'email': 'officer1@somewhere.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)

    def _test_confirm_start(self):
        response = self.client.post('/admin/password_reset/', {'email': 'officer1@somewhere.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        return  self._read_signup_email(mail.outbox[0])

    def test_confirm_valid(self):
        url, path, querydata = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertEquals(response.status_code, 200) 
        self.assert_("Please enter your new password" in response.content)

    def test_confirm_invalid(self):
        url, path, querydata = self._test_confirm_start()
        # Lets munge the path, but still get past URLconf
        path = path[:-33] + ("0"*32) + path[-1]

        response = self.client.get(path)
        self.assertEquals(response.status_code, 200) 
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_invalid_post(self):
        # Same as test_confirm_invalid, but trying
        # to do a POST instead.
        url, path, querydata = self._test_confirm_start()
        path = path[:-33] + ("0"*32) + path[-1]

        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' anewpassword'})
        # Check the password has not been changed 
        u = User.objects.get(email='officer1@somewhere.com')
        self.assert_(not u.check_password("anewpassword"))

    def test_confirm_complete(self):
        url, path, querydata = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        # It redirects us to a 'complete' page:
        self.assertEquals(response.status_code, 302) 
        # Check the password has been changed 
        u = User.objects.get(email='officer1@somewhere.com')
        self.assert_(u.check_password("anewpassword"))

    def test_confirm_different_passwords(self):
        url, path, querydata = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' x'})
        self.assertEquals(response.status_code, 200)
        self.assert_("The two password fields didn't match" in response.content)

    def _read_signup_email(self, email):
        urlmatch = re.search("http://.*/reset/\S*", email.body)
        self.assert_(urlmatch is not None, "No URL found in sent email")
        url = urlmatch.group()
        self.assert_("http://www.cciw.co.uk/" in url)
        path, querydata = url_to_path_and_query(url)
        return url, path, querydata
