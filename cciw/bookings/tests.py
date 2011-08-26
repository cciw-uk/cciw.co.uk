# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson

from cciw.bookings.models import BookingAccount, Price, Booking
from cciw.bookings.models import PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, BOOKING_APPROVED, BOOKING_INFO_COMPLETE, BOOKING_BOOKED
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


class CreatePlaceMixin(LogInMixin):
    place_details = {
        'name': 'Joe Bloggs',
        'sex': 'm',
        'date_of_birth': '1990-01-01',
        'address': 'x',
        'post_code': 'ABC 123',
        'contact_name': 'Mary Bloggs',
        'contact_phone_number': '01982 987654',
        'gp_name': 'Doctor Who',
        'gp_address': 'The Tardis',
        'gp_phone_number': '01234 456789',
        'medical_card_number': 'asdfasdf',
        'agreement': '1',
        'price_type': '0',
        }

    def add_prices(self):
        year = get_thisyear()
        Price.objects.get_or_create(year=year,
                                    price_type=PRICE_FULL,
                                    price=Decimal('100.00'))
        Price.objects.get_or_create(year=year,
                                    price_type=PRICE_2ND_CHILD,
                                    price=Decimal('75.00'))
        Price.objects.get_or_create(year=year,
                                    price_type=PRICE_3RD_CHILD,
                                    price=Decimal('50.00'))

    def create_camp(self):
        # Need to create a Camp that we can choose i.e. is in the future
        Camp.objects.create(year=get_thisyear(), number=1,
                            start_date=datetime.now() + timedelta(20),
                            end_date=datetime.now() + timedelta(27),
                            site_id=1)

    def create_place(self, extra=None):
        # We use public views to create place, to ensure that they are created
        # in the same way that a user would.
        self.login()
        self.add_prices()
        camp = Camp.objects.filter(start_date__gte=datetime.now())[0]

        data = self.place_details.copy()
        data['camp'] = camp.id
        if extra is not None:
            data.update(extra)
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

    def setUp(self):
        super(CreatePlaceMixin, self).setUp()
        self.create_camp()


class TestAddPlace(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

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

    def test_complete(self):
        self.login()
        self.add_prices()
        b = BookingAccount.objects.get(email=self.email)
        camp = Camp.objects.filter(start_date__gte=datetime.now())[0]
        self.assertEqual(b.bookings.count(), 0)

        data = self.place_details.copy()
        data['camp'] = camp.id
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Did we create it?
        self.assertEqual(b.bookings.count(), 1)


class TestEditPlace(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    # Most functionality is shared with the 'add' form, so doesn't need testing separately.

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('cciw.bookings.views.edit_place', kwargs={'id':'1'}))
        self.assertEqual(resp.status_code, 302)

    def test_show_if_owner(self):
        self.login()
        self.add_prices()
        self.create_place()
        acc = BookingAccount.objects.get(email=self.email)
        b = acc.bookings.all()[0]
        resp = self.client.get(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "id_save_btn")

    def test_404_if_not_owner(self):
        self.login()
        self.add_prices()
        self.create_place()
        other_account = BookingAccount.objects.create(email='other@mail.com')
        Booking.objects.all().update(account=other_account)
        b = Booking.objects.all()[0]
        resp = self.client.get(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}))
        self.assertEqual(resp.status_code, 404)

    def test_incomplete(self):
        self.login()
        self.add_prices()
        self.create_place()
        acc = BookingAccount.objects.get(email=self.email)
        b = acc.bookings.all()[0]
        resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_complete(self):
        self.login()
        self.add_prices()
        self.create_place()
        acc = BookingAccount.objects.get(email=self.email)
        b = acc.bookings.all()[0]
        camp = Camp.objects.filter(start_date__gte=datetime.now())[0]

        data = self.place_details.copy()
        data['name'] = "A New Name"
        data['camp'] = camp.id
        resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Did we alter it?
        self.assertEqual(acc.bookings.all()[0].name, "A New Name")

    def test_edit_booked(self):
        """
        Test we can't edit a booking when it is already booked.
        (or anything but BOOKING_INFO_COMPLETE)
        """
        self.login()
        self.add_prices()
        self.create_place()
        acc = BookingAccount.objects.get(email=self.email)
        b = acc.bookings.all()[0]

        for state in [BOOKING_APPROVED, BOOKING_BOOKED]:
            b.state = state
            b.save()

            # Check there is no save button
            resp = self.client.get(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}))
            self.assertNotContains(resp, "id_save_btn")
            # Check for message
            self.assertContains(resp, "can only be changed by an admin.")

            # Attempt a post
            camp = Camp.objects.filter(start_date__gte=datetime.now())[0]
            data = self.place_details.copy()
            data['name'] = "A New Name"
            data['camp'] = camp.id
            resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), data)
            # Check we didn't alter it
            self.assertNotEqual(acc.bookings.all()[0].name, "A New Name")


class TestListBookings(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(302, resp.status_code)

    def test_show_bookings(self):
        self.login()
        self.create_place()
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Joe Bloggs")
        self.assertContains(resp, "£100")
        self.assertContains(resp, "This place can be booked")
        self.assertContains(resp, "id_book_now_btn")

    def test_handle_custom_price(self):
        self.login()
        self.create_place({'price_type': PRICE_CUSTOM})
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Joe Bloggs")
        self.assertContains(resp, "TBA")
        self.assertContains(resp, "A custom discount needs to be arranged by the booking secretary")
        self.assertNotContains(resp, "id_book_now_btn")
        self.assertContains(resp, "This place cannot be booked for the reasons described above")

    def test_2nd_child_discount_allowed(self):
        self.login()
        self.create_place({'price_type': PRICE_2ND_CHILD})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertContains(resp, "You cannot use a 2nd child discount")
        self.assertNotContains(resp, "id_book_now_btn")

        # 2 places, both at 2nd child discount, is not allowed.
        self.create_place({'price_type': PRICE_2ND_CHILD})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertContains(resp, "You cannot use a 2nd child discount")
        self.assertNotContains(resp, "id_book_now_btn")

    def test_3rd_child_discount_allowed(self):
        self.login()
        self.create_place({'price_type': PRICE_FULL})
        self.create_place({'price_type': PRICE_3RD_CHILD})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertContains(resp, "You cannot use a 3rd child discount")
        self.assertNotContains(resp, "id_book_now_btn")

        # 3 places, with 2 at 3rd child discount, is not allowed.
        self.create_place({'price_type': PRICE_3RD_CHILD})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertContains(resp, "You cannot use a 3rd child discount")
        self.assertNotContains(resp, "id_book_now_btn")

    def test_handle_serious_illness(self):
        self.login()
        self.create_place({'serious_illness': '1'})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertContains(resp, "Must be approved by leader due to serious illness/condition")
        self.assertNotContains(resp, "id_book_now_btn")

    def test_handle_two_problem_bookings(self):
        # Test the error we get for more than one problem booking
        self.login()
        self.create_place({'price_type': PRICE_CUSTOM})
        self.create_place({'name': 'Another Child',
                           'price_type': PRICE_CUSTOM})
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Joe Bloggs")
        self.assertContains(resp, "TBA")
        self.assertContains(resp, "A custom discount needs to be arranged by the booking secretary")
        self.assertNotContains(resp, "id_book_now_btn")
        self.assertContains(resp, "These places cannot be booked for the reasons described above")

    def test_handle_mixed_problem_and_non_problem(self):
        # Test the message we get if one place is bookable and the other is not
        self.login()
        self.create_place() # bookable
        self.create_place({'name': 'Another Child',
                           'price_type': PRICE_CUSTOM}) # not bookable
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertNotContains(resp, "id_book_now_btn")
        self.assertContains(resp, "One or more of the places cannot be booked")

    def test_total(self):
        self.login()
        self.create_place()
        self.create_place({'name': 'Another Child'})

        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "£200")

    def test_manually_approved(self):
        # manually approved places should appear as OK to book
        self.login()
        self.create_place() # bookable
        self.create_place({'name': 'Another Child',
                           'price_type': PRICE_CUSTOM}) # not bookable
        Booking.objects.filter(price_type=PRICE_CUSTOM).update(state=BOOKING_APPROVED,
                                                               amount_due=Decimal('0.01'))
        resp = self.client.get(reverse('cciw.bookings.views.list_bookings'))
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Joe Bloggs")
        self.assertContains(resp, "£100")
        self.assertContains(resp, "This place can be booked")

        self.assertContains(resp, "Another Child")
        self.assertContains(resp, "£0.01")

        self.assertContains(resp, "id_book_now_btn")
        # Total:
        self.assertContains(resp, "£100.01")

    def test_add_another_btn(self):
        self.login()
        self.create_place()
        resp = self.client.post(reverse('cciw.bookings.views.list_bookings'), {'add_another': '1'})
        self.assertEqual(302, resp.status_code)
        newpath = reverse('cciw.bookings.views.add_place')
        self.assertTrue(resp['Location'].endswith(newpath))

