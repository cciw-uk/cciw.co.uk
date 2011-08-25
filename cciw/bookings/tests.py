from datetime import datetime, timedelta
from decimal import Decimal

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.bookings.models import BookingAccount, Price
from cciw.bookings.models import PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD
from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp
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

    def test_skip_if_logged_in(self):
        # This assumes verification process works
        def login():
            self.client.post(reverse('cciw.bookings.views.start'),
                             {'email': 'booker@bookers.com'})
            url, path, querydata = read_email_url(mail.outbox[-1], "https?://.*/booking/v/.*")
            self.client.get(path, querydata)
        login()

        # Check redirect to step 3 - account details
        resp = self.client.get(reverse('cciw.bookings.views.start'))
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.account_details')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Check redirect to step 4 - add place
        b = BookingAccount.objects.get(email="booker@bookers.com")
        b.name = "Joe"
        b.address = "Home"
        b.post_code = "XY1 D45"
        b.save()
        resp = self.client.get(reverse('cciw.bookings.views.start'))
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.add_place')
        self.assertTrue(resp['Location'].endswith(newpath))


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
        self.assertTrue(resp['Location'].endswith(newpath))
        self.assertEqual(str(BookingAccount.objects.get(email='booker@bookers.com').id),
                         resp.cookies['bookingaccount'].value.split(':')[0])

    def test_verify_correct_and_has_details(self):
        """
        Test the email verification stage when the URL is correct and the
        account already has name and address
        """
        # Assumes booking_start works:
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': 'booker@bookers.com'})
        b = BookingAccount.objects.get(email='booker@bookers.com')
        b.name = "Joe"
        b.address = "Home"
        b.post_code = "XY1 D45"
        b.save()

        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        resp = self.client.get(path, querydata)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.add_place')
        self.assertTrue(resp['Location'].endswith(newpath))

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


class LogInMixin(object):
    email = 'booker@bookers.com'

    def login(self):
        # Easiest way is to simulate what the user actually has to do
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': self.email})
        url, path, querydata = read_email_url(mail.outbox[-1], "https?://.*/booking/v/.*")
        self.client.get(path, querydata)


class TestAccountDetails(LogInMixin, TestCase):

    fixtures = ['basic.json']

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('cciw.bookings.views.account_details'))
        self.assertEqual(resp.status_code, 302)

    def test_show_if_logged_in(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.account_details'))
        self.assertEqual(resp.status_code, 200)

    def test_missing_name(self):
        self.login()
        resp = self.client.post(reverse('cciw.bookings.views.account_details'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_complete(self):
        """
        Test that we can complete the account details page
        """
        self.login()
        resp = self.client.post(reverse('cciw.bookings.views.account_details'),
                                {'name': 'Mr Booker',
                                 'address': '123, A Street',
                                 'post_code': 'XY1 D45',
                                 })
        self.assertEqual(resp.status_code, 302)
        b = BookingAccount.objects.get(email=self.email)
        self.assertEqual(b.name, 'Mr Booker')


class TestAddPlace(LogInMixin, TestCase):

    fixtures = ['basic.json']

    def add_prices(self):
        year = get_thisyear()
        Price.objects.create(year=year,
                             price_type=PRICE_FULL,
                             price=Decimal('100.00'))
        Price.objects.create(year=year,
                             price_type=PRICE_2ND_CHILD,
                             price=Decimal('75.00'))
        Price.objects.create(year=year,
                             price_type=PRICE_3RD_CHILD,
                             price=Decimal('50.00'))


    def setUp(self):
        super(TestAddPlace, self).setUp()
        # Need to create a Camp that we can choose i.e. is in the future
        Camp.objects.create(year=get_thisyear(), number=1,
                            start_date=datetime.now() + timedelta(20),
                            end_date=datetime.now() + timedelta(27),
                            site_id=1)
        self._ensure_thisyear_reset()

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('cciw.bookings.views.add_place'))
        self.assertEqual(resp.status_code, 302)

    def test_show_if_logged_in(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.add_place'))
        self.assertEqual(resp.status_code, 200)

    def test_show_error_if_no_prices(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.add_place'), follow=True)
        self.assertContains(resp, "prices have not been set")

    def test_post_not_allowed_if_no_prices(self):
        self.login()
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), {}, follow=True)
        self.assertContains(resp, "prices have not been set")

    def test_allowed_if_prices_set(self):
        self.login()
        self.add_prices()
        resp = self.client.get(reverse('cciw.bookings.views.add_place'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Prices have not been set")

    def test_incomplete(self):
        self.login()
        self.add_prices()
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_old_camp(self):
        self.login()
        # TODO

    place_details = {
        'name': 'Joe',
        'sex': 'm',
        'date_of_birth': '1990-01-01',
        'address': 'x',
        'post_code': 'ABC 123',
        'contact_name': 'Mary',
        'contact_phone_number': '01982 987654',
        'gp_name': 'Doctor Who',
        'gp_address': 'The Tardis',
        'gp_phone_number': '01234 456789',
        'medical_card_number': 'asdfasdf',
        'agreement': '1',
        'price_type': '0',
        }

    def _ensure_thisyear_reset(self):
        from cciw.cciwmain import common
        common._thisyear = None

    def test_complete(self):
        self.login()
        self.add_prices()
        b = BookingAccount.objects.get(email=self.email)
        camp = Camp.objects.filter(start_date__gte=datetime.now())[0]
        self.assertEqual(b.booking_set.count(), 0)

        data = self.place_details.copy()
        data['camp'] = camp.id
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Did we create it?
        self.assertEqual(b.booking_set.count(), 1)

    def test_old_camp_year(self):
        self.login()
        self.add_prices()
        b = BookingAccount.objects.get(email=self.email)
        self.assertEqual(b.booking_set.count(), 0)

        data = self.place_details.copy()
        data['camp'] = 1 # an old camp
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), data)
        self.assertEqual(resp.status_code, 200)
        year = get_thisyear()
        self.assertContains(resp, 'Only a camp in %s can be selected' % year)
