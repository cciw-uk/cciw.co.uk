from django.test import TestCase
from django.core import mail
from references import OFFICER
import re
from django.contrib.auth.models import User
from cciw.cciwmain.tests.members import url_to_path_and_query

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

    def test_confirm(self):
        response = self.client.post('/admin/password_reset/', {'email': 'officer1@somewhere.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        url, path, querydata, password = self._read_signup_email(mail.outbox[0])

        # Check the password has not been changed yet
        u = User.objects.get(email='officer1@somewhere.com')
        self.assert_(not u.check_password(password))

        response = self.client.get(path, querydata)
        self.assertEquals(response.status_code, 200)

        # Check password has changed now
        u = User.objects.get(email='officer1@somewhere.com')
        self.assert_(u.check_password(password))

    def _read_signup_email(self, email):
        urlmatch = re.search("http://.*/confirm/.*\w", email.body)
        self.assert_(urlmatch is not None, "No URL found in sent email")
        passwordmatch = re.search("Your new password is:\s*(\S*)\s*", email.body)
        self.assert_(passwordmatch is not None, "No password in sent email")
        url = urlmatch.group()
        self.assert_("http://www.cciw.co.uk/" in url)
        path, querydata = url_to_path_and_query(url)
        return url, path, querydata, passwordmatch.groups()[0]

