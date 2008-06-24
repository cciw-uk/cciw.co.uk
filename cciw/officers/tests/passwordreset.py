from django.test import TestCase
from django.core import mail
from references import OFFICER

class PasswordResetTest(TestCase):
    fixtures = ['officers_users.yaml']
    def test_email_not_found(self):
        response = self.client.get('/admin/password_reset/')
        self.assertEquals(response.status_code, 200)
        response = self.client.post('/admin/password_reset/', {'email': 'not_a_real_email@email.com'} )
        self.assertContains(response, "That e-mail address doesn't have an associated user account")
        self.assertEquals(len(mail.outbox), 0)

    def test_email_found(self):
        response = self.client.post('/admin/password_reset/', {'email': 'officer1@somewhere.com'} )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
