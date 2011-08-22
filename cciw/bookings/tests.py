from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.bookings.models import BookingAccount


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

