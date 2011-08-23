from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.bookings.models import BookingAccount
from cciw.cciwmain.tests.mailhelpers import read_email_url


class TestBookingStart(TestCase):

    fixtures = ['basic.json']

    def test_show_form(self):
        resp = self.client.get(reverse('cciw.bookings.views.start'))
        self.assertEqual(resp.status_code, 200)

        self.assertContains(resp, 'id_email')

    def test_complete_form(self):
        self.assertEqual(BookingAccount.objects.all().count(), 0)
        resp = self.client.post(reverse('cciw.bookings.views.start'),
                                {'email': 'booker@bookers.com'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        b = BookingAccount.objects.get(email='booker@bookers.com')
        self.assertEqual(b.activated, None)
        self.assertEqual(len(mail.outbox), 1)

    def test_complete_form_existing_email(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        resp = self.client.post(reverse('cciw.bookings.views.start'),
                                {'email': 'booker@bookers.com'})
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)


class TestBookingVerify(TestCase):

    fixtures = ['basic.json']

    def _read_email_verify_email(self, email):
        return read_email_url(email, "https?://.*/booking/v/.*")

    def test_verify_correct(self):
        """
        Test the email verification stage when the URL is correct
        """
        # Assumes booking_start works:
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': 'booker@bookers.com'})
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        resp = self.client.get(path, querydata)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.account_details')
        self.assertEqual(resp['Location'][-len(newpath):], newpath)
        self.assertEqual(str(BookingAccount.objects.get(email='booker@bookers.com').id),
                         resp.cookies['bookingaccount'].value.split(':')[0])

    def test_verify_incorrect(self):
        """
        Test the email verification stage when the URL is incorrect
        """
        # Assumes booking_start works:
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': 'booker@bookers.com'})
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        badpath = path.replace('-', '-1')
        resp = self.client.get(badpath, querydata, follow=True)
        self.assertContains(resp, "failed")
        self.assertTrue('bookingaccount' not in resp.cookies)

    def test_verify_invalid_account(self):
        """
        Test the email verification stage when the URL contains an invalid
        BookingAccount id
        """
        # Assumes booking_start works:
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': 'booker@bookers.com'})
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        b = BookingAccount.objects.get(email='booker@bookers.com')
        badpath = path.replace('%s-' % b.id, '1000-')
        resp = self.client.get(badpath, querydata, follow=True)
        self.assertContains(resp, "failed")
        self.assertTrue('bookingaccount' not in resp.cookies)
