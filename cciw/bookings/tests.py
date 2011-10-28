# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
import re

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson

from cciw.bookings.management.commands.expire_bookings import Command as ExpireBookingsCommand
from cciw.bookings.models import BookingAccount, Price, Booking, Payment, ChequePayment, RefundPayment, book_basket_now
from cciw.bookings.models import PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, PRICE_SOUTH_WALES_TRANSPORT, PRICE_DEPOSIT, BOOKING_APPROVED, BOOKING_INFO_COMPLETE, BOOKING_BOOKED, BOOKING_CANCELLED, BOOKING_CANCELLED_FULL_REFUND
from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.officers.tests.references import OFFICER_USERNAME, OFFICER_PASSWORD, BOOKING_SEC_USERNAME, BOOKING_SEC_PASSWORD
from cciw.sitecontent.models import HtmlChunk


DISABLED_BOOK_NOW_BTN = "id_book_now_btn\" disabled>"
ENABLED_BOOK_NOW_BUTTON = "id_book_now_btn\">"


### Mixins to reduce duplication ###

class CreateCampMixin(object):

    camp_minimum_age = 11
    camp_maximum_age = 17

    def create_camp(self):
        # Need to create a Camp that we can choose i.e. is in the future
        self.camp = Camp.objects.create(year=get_thisyear(), number=1,
                                        minimum_age=self.camp_minimum_age,
                                        maximum_age=self.camp_maximum_age,
                                        start_date=datetime.now() + timedelta(20),
                                        end_date=datetime.now() + timedelta(27),
                                        site_id=1)


class CreatePricesMixin(object):
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
        Price.objects.get_or_create(year=year,
                                    price_type=PRICE_SOUTH_WALES_TRANSPORT,
                                    price=Decimal('20.00'))
        Price.objects.get_or_create(year=year,
                                    price_type=PRICE_DEPOSIT,
                                    price=Decimal('20.00'))


class LogInMixin(object):
    email = 'booker@bookers.com'

    def login(self, add_account_details=True):
        if hasattr(self, '_logged_in'):
            return
        # Easiest way is to simulate what the user actually has to do
        self.client.post(reverse('cciw.bookings.views.start'),
                         {'email': self.email})
        url, path, querydata = read_email_url(mail.outbox[-1], "https?://.*/booking/v/.*")
        mail.outbox.pop()
        self.client.get(path, querydata)
        if add_account_details:
            BookingAccount.objects.filter(email=self.email).update(name='Joe',
                                                                   address='123',
                                                                   post_code='XYZ')
        self._logged_in = True

    def get_account(self):
        return BookingAccount.objects.get(email=self.email)


class CreatePlaceMixin(CreatePricesMixin, CreateCampMixin, LogInMixin):
    @property
    def place_details(self):
        return {
            'camp': self.camp.id,
            'first_name': u'Frédéric',
            'last_name': u'Bloggs',
            'sex': 'm',
            'date_of_birth': '%d-01-01' % (get_thisyear() - 14),
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

    def create_place(self, extra=None):
        # We use public views to create place, to ensure that they are created
        # in the same way that a user would.
        self.login()
        self.add_prices()

        data = self.place_details.copy()
        if extra is not None:
            data.update(extra)

        # Sanity check:
        resp0 = self.client.get(reverse('cciw.bookings.views.add_place'))
        self.assertEqual(resp0.status_code, 200)
        resp = self.client.post(reverse('cciw.bookings.views.add_place'), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

    def setUp(self):
        super(CreatePlaceMixin, self).setUp()
        self.create_camp()


### Test cases ###


class TestBookingIndex(CreatePricesMixin, CreateCampMixin, TestCase):

    fixtures = ['basic.json']

    def setUp(self):
        super(TestBookingIndex, self).setUp()
        HtmlChunk.objects.get_or_create(name="bookingform_post_to")

    def test_show_with_no_prices(self):
        resp = self.client.get(reverse('cciw.bookings.views.index'))
        self.assertContains(resp, "Prices for %d have not been finalised yet" % get_thisyear())


    def test_show_with_prices(self):
        self.add_prices()
        self.create_camp() # need for booking to be open
        resp = self.client.get(reverse('cciw.bookings.views.index'))
        self.assertContains(resp, "£100")
        self.assertContains(resp, "£20") # Deposit price


class TestBookingStart(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.start')

    def test_show_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        self.assertContains(resp, 'id_email')

    def test_complete_form(self):
        self.assertEqual(BookingAccount.objects.all().count(), 0)
        resp = self.client.post(self.url,
                                {'email': 'booker@bookers.com'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        b = BookingAccount.objects.get(email='booker@bookers.com')
        self.assertEqual(len(mail.outbox), 1)

    def test_complete_form_existing_email(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        resp = self.client.post(self.url,
                                {'email': 'booker@bookers.com'})
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_skip_if_logged_in(self):
        # This assumes verification process works
        # Check redirect to step 3 - account details
        self.login(add_account_details=False)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.account_details')
        self.assertTrue(resp['Location'].endswith(newpath))

    def test_skip_if_account_details(self):
        # Check redirect to step 4 - add place
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.add_place')
        self.assertTrue(resp['Location'].endswith(newpath))

    def test_skip_if_has_place_details(self):
        # Check redirect to step 5 - checkout
        self.login()
        self.create_place()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].endswith(reverse('cciw.bookings.views.list_bookings')))

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
        acc = BookingAccount.objects.get(email='booker@bookers.com')
        self.assertTrue(acc.last_login is None)
        self.assertTrue(acc.first_login is None)
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        resp = self.client.get(path, querydata)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.account_details')
        self.assertTrue(resp['Location'].endswith(newpath))
        acc = BookingAccount.objects.get(email='booker@bookers.com')
        self.assertEqual(str(acc.id),
                         resp.cookies['bookingaccount'].value.split(':')[0])
        self.assertTrue(acc.last_login is not None)
        self.assertTrue(acc.first_login is not None)


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


class TestAccountDetails(LogInMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.account_details')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_show_if_logged_in(self):
        self.login(add_account_details=False)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_missing_name(self):
        self.login(add_account_details=False)
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_complete(self):
        """
        Test that we can complete the account details page
        """
        self.login(add_account_details=False)
        resp = self.client.post(self.url,
                                {'name': 'Mr Booker',
                                 'address': '123, A Street',
                                 'post_code': 'XY1 D45',
                                 })
        self.assertEqual(resp.status_code, 302)
        b = BookingAccount.objects.get(email=self.email)
        self.assertEqual(b.name, 'Mr Booker')


class TestAddPlace(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.add_place')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_redirect_if_no_account_details(self):
        self.login(add_account_details=False)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_show_if_logged_in(self):
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_show_error_if_no_prices(self):
        self.login()
        resp = self.client.get(self.url, follow=True)
        self.assertContains(resp, "prices have not been set")

    def test_post_not_allowed_if_no_prices(self):
        self.login()
        resp = self.client.post(self.url, {}, follow=True)
        self.assertContains(resp, "prices have not been set")

    def test_allowed_if_prices_set(self):
        self.login()
        self.add_prices()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Prices have not been set")

    def test_incomplete(self):
        self.login()
        self.add_prices()
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_complete(self):
        self.login()
        self.add_prices()
        b = BookingAccount.objects.get(email=self.email)
        self.assertEqual(b.bookings.count(), 0)

        data = self.place_details.copy()
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Did we create it?
        self.assertEqual(b.bookings.count(), 1)

        # Check amount_due
        self.assertEqual(b.bookings.all()[0].amount_due, Price.objects.get(price_type=PRICE_FULL,
                                                                           year=get_thisyear()).price)

    def test_south_wales_surcharge(self):
        self.login()
        self.add_prices()
        b = BookingAccount.objects.get(email=self.email)
        self.assertEqual(b.bookings.count(), 0)

        data = self.place_details.copy()
        data['south_wales_transport'] = '1'
        resp = self.client.post(self.url, data)
        p = Price.objects.get(price_type=PRICE_FULL, year=get_thisyear()).price + \
            Price.objects.get(price_type=PRICE_SOUTH_WALES_TRANSPORT, year=get_thisyear()).price
        self.assertEqual(b.bookings.all()[0].amount_due, p)


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
        acc = self.get_account()
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
        acc = self.get_account()
        b = acc.bookings.all()[0]
        resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required")

    def test_complete(self):
        self.login()
        self.add_prices()
        self.create_place()
        acc = self.get_account()
        b = acc.bookings.all()[0]

        data = self.place_details.copy()
        data['first_name'] = "A New Name"
        resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), data)
        self.assertEqual(resp.status_code, 302)
        newpath = reverse('cciw.bookings.views.list_bookings')
        self.assertTrue(resp['Location'].endswith(newpath))

        # Did we alter it?
        self.assertEqual(acc.bookings.all()[0].first_name, "A New Name")

    def test_edit_booked(self):
        """
        Test we can't edit a booking when it is already booked.
        (or anything but BOOKING_INFO_COMPLETE)
        """
        self.login()
        self.add_prices()
        self.create_place()
        acc = self.get_account()
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
            data = self.place_details.copy()
            data['first_name'] = "A New Name"
            resp = self.client.post(reverse('cciw.bookings.views.edit_place', kwargs={'id':str(b.id)}), data)
            # Check we didn't alter it
            self.assertNotEqual(acc.bookings.all()[0].first_name, "A New Name")


class TestListBookings(CreatePlaceMixin, TestCase):
    # This includes tests for most of the business logic

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.list_bookings')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(self.url)
        self.assertEqual(302, resp.status_code)

    def test_show_bookings(self):
        self.login()
        self.create_place()
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Frédéric Bloggs")
        self.assertContains(resp, "£100")
        self.assertContains(resp, "This place can be booked")
        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)

    def test_handle_custom_price(self):
        self.login()
        self.create_place({'price_type': PRICE_CUSTOM})
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Frédéric Bloggs")
        self.assertContains(resp, "TBA")
        self.assertContains(resp, "A custom discount needs to be arranged by the booking secretary")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)
        self.assertContains(resp, "This place cannot be booked for the reasons described above")

    def test_2nd_child_discount_allowed(self):
        self.login()
        self.create_place({'price_type': PRICE_2ND_CHILD})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You cannot use a 2nd child discount")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

        # 2 places, both at 2nd child discount, is not allowed.
        self.create_place({'price_type': PRICE_2ND_CHILD})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You cannot use a 2nd child discount")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_3rd_child_discount_allowed(self):
        self.login()
        self.create_place({'price_type': PRICE_FULL})
        self.create_place({'price_type': PRICE_3RD_CHILD})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You cannot use a 3rd child discount")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

        # 3 places, with 2 at 3rd child discount, is not allowed.
        self.create_place({'price_type': PRICE_3RD_CHILD})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You cannot use a 3rd child discount")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_handle_serious_illness(self):
        self.login()
        self.create_place({'serious_illness': '1'})

        resp = self.client.get(self.url)
        self.assertContains(resp, "Must be approved by leader due to serious illness/condition")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_minimum_age(self):
        self.login()
        # if born Aug 31st 2001, and thisyear == 2012, should be allowed on camp with
        # minimum_age == 11
        Booking.objects.all().delete()
        self.create_place({'date_of_birth': '%d-08-31' %
                           (get_thisyear() - self.camp_minimum_age)})
        resp = self.client.get(self.url)
        self.assertNotContains(resp, "below the minimum age")

        # if born 1st Sept 2001, and thisyear == 2012, should not be allowed on camp with
        # minimum_age == 11
        Booking.objects.all().delete()
        self.create_place({'date_of_birth': '%d-09-01' %
                           (get_thisyear() - self.camp_minimum_age)})
        resp = self.client.get(self.url)
        self.assertContains(resp, "below the minimum age")

    def test_maximum_age(self):
        self.login()
        # if born 1st Sept 2001, and thisyear == 2019, should be allowed on camp with
        # maximum_age == 17
        Booking.objects.all().delete()
        self.create_place({'date_of_birth': '%d-09-01' %
                           (get_thisyear() - (self.camp_maximum_age + 1))})
        resp = self.client.get(self.url)
        self.assertNotContains(resp, "above the maximum age")

        # if born Aug 31st 2001, and thisyear == 2019, should not be allowed on camp with
        # maximum_age == 17
        Booking.objects.all().delete()
        self.create_place({'date_of_birth': '%d-08-31' %
                           (get_thisyear() - (self.camp_maximum_age + 1))})
        resp = self.client.get(self.url)
        self.assertContains(resp, "above the maximum age")

    def test_no_places_left(self):
        self.login()
        for i in range(0, self.camp.max_campers):
            self.create_place({'sex':'m'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'m'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are no places left on this camp")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

        # Don't want a redundant message
        self.assertNotContains(resp, "There are no places left for boys")

    def test_no_male_places_left(self):
        self.login()
        for i in range(0, self.camp.max_male_campers):
            self.create_place({'sex': 'm'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'m'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are no places left for boys")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

        # Check that we can still book female places
        Booking.objects.filter(state=BOOKING_INFO_COMPLETE).delete()
        self.create_place({'sex':'f'})
        resp = self.client.get(self.url)
        self.assertNotContains(resp, "There are no places left")
        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)

    def test_no_female_places_left(self):
        self.login()
        for i in range(0, self.camp.max_female_campers):
            self.create_place({'sex': 'f'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'f'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are no places left for girls")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_not_enough_places_left(self):
        self.login()
        for i in range(0, self.camp.max_campers - 1):
            self.create_place({'sex':'m'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'f'})
        self.create_place({'sex':'f'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are not enough places left on this camp")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_not_enough_male_places_left(self):
        self.login()
        for i in range(0, self.camp.max_male_campers - 1):
            self.create_place({'sex':'m'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'m'})
        self.create_place({'sex':'m'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are not enough places for boys left on this camp")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_not_enough_female_places_left(self):
        self.login()
        for i in range(0, self.camp.max_female_campers - 1):
            self.create_place({'sex':'f'})
        self.camp.bookings.update(state=BOOKING_BOOKED)

        self.create_place({'sex':'f'})
        self.create_place({'sex':'f'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "There are not enough places for girls left on this camp")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)

    def test_handle_two_problem_bookings(self):
        # Test the error we get for more than one problem booking
        self.login()
        self.create_place({'price_type': PRICE_CUSTOM})
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child',
                           'price_type': PRICE_CUSTOM})
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Frédéric Bloggs")
        self.assertContains(resp, "TBA")
        self.assertContains(resp, "A custom discount needs to be arranged by the booking secretary")
        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)
        self.assertContains(resp, "These places cannot be booked for the reasons described above")

    def test_handle_mixed_problem_and_non_problem(self):
        # Test the message we get if one place is bookable and the other is not
        self.login()
        self.create_place() # bookable
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child',
                           'price_type': PRICE_CUSTOM}) # not bookable
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, DISABLED_BOOK_NOW_BTN)
        self.assertContains(resp, "One or more of the places cannot be booked")

    def test_total(self):
        self.login()
        self.create_place()
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child'})

        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "£200")

    def test_manually_approved(self):
        # manually approved places should appear as OK to book
        self.login()
        self.create_place() # bookable
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child',
                           'price_type': PRICE_CUSTOM}) # not bookable
        Booking.objects.filter(price_type=PRICE_CUSTOM).update(state=BOOKING_APPROVED,
                                                               amount_due=Decimal('0.01'))
        resp = self.client.get(self.url)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Camp 1")
        self.assertContains(resp, "Frédéric Bloggs")
        self.assertContains(resp, "£100")
        self.assertContains(resp, "This place can be booked")

        self.assertContains(resp, "Another Child")
        self.assertContains(resp, "£0.01")

        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)
        # Total:
        self.assertContains(resp, "£100.01")

    def test_add_another_btn(self):
        self.login()
        self.create_place()
        resp = self.client.post(self.url, {'add_another': '1'})
        self.assertEqual(302, resp.status_code)
        newpath = reverse('cciw.bookings.views.add_place')
        self.assertTrue(resp['Location'].endswith(newpath))

    def test_move_to_shelf(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.shelved, False)
        resp = self.client.post(self.url)

        # Move to shelf button should be there
        self.assertContains(resp, "name=\"shelve_%s\"" % b.id)

        # Now click it
        resp2 = self.client.post(self.url, {'shelve_%s' % b.id: '1'})

        # Should be changed
        b2 = acc.bookings.all()[0]
        self.assertEqual(b2.shelved, True)

        # Different button should appear
        self.assertNotContains(resp2, "name=\"shelve_%s\"" % b.id)
        self.assertContains(resp2, "name=\"unshelve_%s\"" % b.id)

        self.assertContains(resp2, "<h2>Shelf</h2>")

    def test_move_to_basket(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        b.shelved = True
        b.save()

        # Move to basket button should be there
        resp = self.client.get(self.url)
        self.assertContains(resp, "name=\"unshelve_%s\"" % b.id)

        # Now click it
        resp2 = self.client.post(self.url, {'unshelve_%s' % b.id: '1'})

        # Should be changed
        b2 = acc.bookings.all()[0]
        self.assertEqual(b2.shelved, False)

        # Shelf section should disappear.
        self.assertNotContains(resp2, "<h2>Shelf</h2>")

    def test_delete_place(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        resp = self.client.post(self.url)

        # Delete button should be there
        self.assertContains(resp, "name=\"delete_%s\"" % b.id)

        # Now click it
        resp2 = self.client.post(self.url, {'delete_%s' % b.id: '1'})

        # Should be gone
        self.assertEqual(0, acc.bookings.count())

    def test_edit_place_btn(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        resp = self.client.post(self.url)

        # Delete button should be there
        self.assertContains(resp, "name=\"edit_%s\"" % b.id)

        # Now click it
        resp2 = self.client.post(self.url, {'edit_%s' % b.id: '1'})
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(resp2['Location'].endswith(reverse('cciw.bookings.views.edit_place', kwargs={'id':b.id})))

    def test_book_ok(self):
        """
        Test that we can book a place
        """
        self.login()
        self.create_place()
        resp = self.client.get(self.url)
        state_token = re.search(r'name="state_token" value="(.*)"', resp.content).groups()[0]
        resp2 = self.client.post(self.url, {'state_token': state_token,
                                            'book_now': '1'})
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BOOKING_BOOKED)
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(resp2['Location'].endswith(reverse('cciw.bookings.views.pay')))

    def test_book_unbookable(self):
        """
        Test that an unbookable place can't be booked
        """
        self.login()
        self.create_place({'serious_illness': '1'})
        resp = self.client.get(self.url)
        state_token = re.search(r'name="state_token" value="(.*)"', resp.content).groups()[0]
        resp2 = self.client.post(self.url, {'state_token': state_token,
                                            'book_now': '1'})
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BOOKING_INFO_COMPLETE)
        self.assertContains(resp2, "These places cannot be booked")

    def test_book_one_unbookable(self):
        """
        Test that if one places is unbookable, no place can be booked
        """
        self.login()
        self.create_place()
        self.create_place({'serious_illness': '1'})
        resp = self.client.get(self.url)
        state_token = re.search(r'name="state_token" value="(.*)"', resp.content).groups()[0]
        resp2 = self.client.post(self.url, {'state_token': state_token,
                                            'book_now': '1'})
        acc = self.get_account()
        for b in acc.bookings.all():
            self.assertEqual(b.state, BOOKING_INFO_COMPLETE)
        self.assertContains(resp2, "These places cannot be booked")

    def test_same_name_same_camp(self):
        self.login()
        self.create_place()
        self.create_place() # Identical

        resp = self.client.get(self.url)
        self.assertContains(resp, "You have entered another set of place details for a camper called")
        # This is only a warning:
        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)

    def test_warn_about_multiple_full_price(self):
        self.login()
        self.create_place()
        self.create_place({'first_name': 'Mary',
                           'last_name': 'Bloggs'})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You have multiple places at &#39;Full price")
        self.assertContains(resp, "If Mary Bloggs and Frédéric Bloggs")
        # This is only a warning:
        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)

        # Check for more than 2
        self.create_place({'first_name': 'Peter',
                           'last_name': 'Bloggs'})
        resp = self.client.get(self.url)
        self.assertContains(resp, "If Mary Bloggs, Peter Bloggs and Frédéric Bloggs")

    def test_warn_about_multiple_2nd_child(self):
        self.login()
        self.create_place()
        self.create_place({'first_name': 'Mary',
                           'last_name': 'Bloggs',
                           'price_type': PRICE_2ND_CHILD})
        self.create_place({'first_name': 'Peter',
                           'last_name': 'Bloggs',
                           'price_type': PRICE_2ND_CHILD})

        resp = self.client.get(self.url)
        self.assertContains(resp, "You have multiple places at &#39;2nd child")
        self.assertContains(resp, "If Peter Bloggs and Mary Bloggs")
        self.assertContains(resp, "one is eligible")
        # This is only a warning:
        self.assertContains(resp, ENABLED_BOOK_NOW_BUTTON)


        self.create_place({'first_name': 'Zac',
                           'last_name': 'Bloggs',
                           'price_type': PRICE_2ND_CHILD})
        resp = self.client.get(self.url)
        self.assertContains(resp, "2 are eligible")


    def test_book_now_safeguard(self):
        # It might be possible to alter the list of items in the basket in one
        # tab, and then press 'Book now' from an out-of-date representation of
        # the basket. We need a safeguard against this.

        # Must include at least id,price,camp choice for each booking
        self.login()
        self.create_place()
        resp = self.client.get(self.url)
        state_token = re.search(r'name="state_token" value="(.*)"', resp.content).groups()[0]

        # Now modify
        acc = self.get_account()
        b = acc.bookings.all()[0]
        b.south_wales_transport = True
        b.auto_set_amount_due()
        b.save()

        resp2 = self.client.post(self.url, {'state_token': state_token,
                                            'book_now': '1'})

        # Should not be modified
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BOOKING_INFO_COMPLETE)
        self.assertContains(resp2, "Places were not booked due to modifications made")

    def test_book_with_money_in_account(self):
        self.login()
        self.create_place()

        # Put some money in my account.
        acc = self.get_account()
        acc.receive_payment(acc.bookings.all()[0].amount_due)
        acc.save()

        # Book
        resp = self.client.get(self.url)
        state_token = re.search(r'name="state_token" value="(.*)"', resp.content).groups()[0]

        resp2 = self.client.post(self.url, {'state_token': state_token,
                                            'book_now': '1'},
                                 follow=True)

        # Place should be booked AND should not expire
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BOOKING_BOOKED)
        self.assertEqual(b.booking_expires, None)

        # balance should be zero
        acc = self.get_account()
        self.assertEqual(acc.get_balance(), Decimal('0.00'))
        self.assertEqual(acc.get_balance(confirmed_only=True), Decimal('0.00'))


class TestPay(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.list_bookings')

    def test_balance_empty(self):
        self.login()
        self.add_prices()
        resp = self.client.get(reverse('cciw.bookings.views.pay'))
        self.assertContains(resp, '£0.00')

    def test_balance_after_booking(self):
        self.login()
        self.create_place()
        self.create_place()
        acc = self.get_account()
        acc.bookings.all().update(state=BOOKING_BOOKED)

        resp = self.client.get(reverse('cciw.bookings.views.pay'))

        # 2 places:
        expected_price = 2 * Price.objects.get(year=get_thisyear(),
                                               price_type=PRICE_FULL).price
        self.assertContains(resp, '£%s' % expected_price)


class TestPayReturnPoints(LogInMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.list_bookings')

    def test_pay_done(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.pay_done'))
        self.assertEqual(resp.status_code, 200)
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse('cciw.bookings.views.pay_done'), {})
        self.assertEqual(resp.status_code, 200)

    def test_pay_cancelled(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.pay_cancelled'))
        self.assertEqual(resp.status_code, 200)
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse('cciw.bookings.views.pay_cancelled'), {})
        self.assertEqual(resp.status_code, 200)


class TestPaymentReceived(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    def test_receive_payment(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        book_basket_now(acc.bookings.basket(self.camp.year))
        self.assertTrue(acc.bookings.all()[0].booking_expires is not None)

        p = Price.objects.get(year=get_thisyear(), price_type=PRICE_FULL).price
        acc.receive_payment(p)

        acc = self.get_account()

        # Check we updated the account
        self.assertEqual(acc.total_received, p)

        # Check we updated the bookings
        self.assertTrue(acc.bookings.all()[0].booking_expires is None)

    def test_insufficient_receive_payment(self):
        self.login()
        self.create_place()
        self.create_place({'price_type': PRICE_2ND_CHILD})
        acc = self.get_account()
        book_basket_now(acc.bookings.basket(self.camp.year))
        self.assertTrue(acc.bookings.all()[0].booking_expires is not None)

        p1 = Price.objects.get(year=get_thisyear(), price_type=PRICE_FULL).price
        p2 = Price.objects.get(year=get_thisyear(), price_type=PRICE_2ND_CHILD).price

        # Between the two
        p = (p1 + p2) / 2
        acc.receive_payment(p)

        # Check we updated the account
        self.assertEqual(acc.total_received, p)

        # Check we updated the one we had enough funds for
        self.assertTrue(acc.bookings.filter(price_type=PRICE_2ND_CHILD)[0].booking_expires is None)
        # but not the one which was too much.
        self.assertTrue(acc.bookings.filter(price_type=PRICE_FULL)[0].booking_expires is not None)


        # We can rectify it with a payment of the rest
        acc.receive_payment((p1 + p2) - p)
        self.assertTrue(acc.bookings.filter(price_type=PRICE_FULL)[0].booking_expires is None)

    def test_email_for_bad_payment_1(self):
        from cciw.bookings.models import paypal_payment_received

        class IpnMock(object):
            pass

        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal('1.00')
        ipn_1.custom = "x" # wrong format

        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        paypal_payment_received(ipn_1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('/admin/ipn/paypal' in mail.outbox[0].body)

    def test_email_for_bad_payment_2(self):
        from cciw.bookings.models import paypal_payment_received

        class IpnMock(object):
            pass

        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal('1.00')
        ipn_1.custom = "account:1234;" # bad id

        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        paypal_payment_received(ipn_1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('/admin/ipn/paypal' in mail.outbox[0].body)

    def test_receive_payment_handler(self):
        # Use the actual signal handler, check the good path.
        from cciw.bookings.models import paypal_payment_received
        self.login()

        from paypal.standard.ipn.models import PayPalIPN
        class IpnMock(object):
            pass

        ipn_1 = PayPalIPN.objects.create(mc_gross = Decimal('1.00'),
                                         custom = "account:%s;" % self.get_account().id,
                                         ipaddress='127.0.0.1',
                                         )
        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        paypal_payment_received(ipn_1)

        # Since payments are processed in a separate process, we cannot
        # test that the account was updated in this process.
        # But we can test for Payment objects
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, ipn_1.mc_gross)

    def test_email_for_good_payment(self):
        # This email could be triggered by whenever BookingAccount.distribute_funds
        # is called, which can be from multiple routes. So we test it directly.

        self.login()
        self.create_place()
        acc = self.get_account()
        book_basket_now(acc.bookings.basket(self.camp.year))

        mail.outbox = []
        acc.receive_payment(acc.bookings.all()[0].amount_due)

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(mail.outbox[0].subject, "CCIW booking - place confirmed")
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertTrue("Thank you for your payment" in mail.outbox[0].body)

    def test_only_one_email_for_multiple_places(self):
        self.login()
        self.create_place()
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child'})

        acc = self.get_account()
        book_basket_now(acc.bookings.basket(self.camp.year))

        mail.outbox = []
        acc.receive_payment(acc.get_balance())

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(mail.outbox[0].subject, "CCIW booking - place confirmed")
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertTrue(self.place_details['first_name'] in mail.outbox[0].body)
        self.assertTrue('Another Child' in mail.outbox[0].body)

    def test_concurrent_save(self):
        acc1 = BookingAccount.objects.create(email='foo@foo.com')
        acc2 = BookingAccount.objects.get(email='foo@foo.com')

        acc1.receive_payment(Decimal('100.00'))

        self.assertEqual(BookingAccount.objects.get(email='foo@foo.com').total_received,
                         Decimal('100.00'))

        acc2.save() # this will have total_received = 0.00

        self.assertEqual(BookingAccount.objects.get(email='foo@foo.com').total_received,
                         Decimal('100.00'))


class TestAjaxViews(CreatePlaceMixin, TestCase):
    # Basic tests to ensure that the views that serve AJAX return something
    # sensible

    fixtures = ['basic.json', 'officers_users.json']

    def test_places_json(self):
        self.login()
        self.create_place()
        resp = self.client.get(reverse('cciw.bookings.views.places_json'))
        json = simplejson.loads(resp.content)
        self.assertEqual(json['places'][0]['first_name'], self.place_details['first_name'])

    def test_places_json_with_exclusion(self):
        self.login()
        self.create_place()
        acc = self.get_account()
        resp = self.client.get(reverse('cciw.bookings.views.places_json') +
                               ("?exclude=%d" % acc.bookings.all()[0].id))
        json = simplejson.loads(resp.content)
        self.assertEqual(json['places'], [])

    def test_places_json_with_bad_exclusion(self):
        self.login()
        resp = self.client.get(reverse('cciw.bookings.views.places_json') +"?exclude=x")
        json = simplejson.loads(resp.content)
        self.assertEqual(json['places'], [])

    def test_account_json(self):
        self.login()
        acc = self.get_account()
        acc.address = '123 Main Street'
        acc.save()

        resp = self.client.get(reverse('cciw.bookings.views.account_json'))
        json = simplejson.loads(resp.content)
        self.assertEqual(json['account']['address'], '123 Main Street')

    def test_all_account_json(self):
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             post_code="ABC",
                                             name="Mr Foo")
        acc2 = BookingAccount.objects.create(email="goo@foo.com",
                                             post_code="XYZ",
                                             name="Mr Goo")

        self.client.login(username=OFFICER_USERNAME, password=OFFICER_PASSWORD)
        resp = self.client.get(reverse('cciw.bookings.views.all_account_json'))
        self.assertEqual(resp.status_code, 403)

        # Now as booking secretary
        self.client.login(username=BOOKING_SEC_USERNAME, password=BOOKING_SEC_PASSWORD)
        resp = self.client.get(reverse('cciw.bookings.views.all_account_json') + "?id=%d" % acc1.id)
        self.assertEqual(resp.status_code, 200)

        json = simplejson.loads(resp.content)
        self.assertEqual(json['account']['post_code'], 'ABC')

    def test_booking_problems(self):
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SEC_USERNAME, password=BOOKING_SEC_PASSWORD)
        resp = self.client.post(reverse('cciw.bookings.views.booking_problems_json'),
                                {'account':str(acc1.id)})


        self.assertEqual(resp.status_code, 200)
        json = simplejson.loads(resp.content)
        self.assertEqual(json['valid'], False)

        data = self.place_details.copy()
        data['account'] = str(acc1.id)
        data['created_0'] = '1970-01-01' # Simulate form, which doesn't supply created
        data['created_1'] = '00:00:00'
        data['state'] = BOOKING_APPROVED
        data['amount_due'] = '100.00'
        data['price_type'] = PRICE_CUSTOM
        resp = self.client.post(reverse('cciw.bookings.views.booking_problems_json'),
                                data)

        json = simplejson.loads(resp.content)
        self.assertEqual(json['valid'], True)
        problems = json['problems']
        self.assertTrue(u"A custom discount needs to be arranged by the booking secretary" in
                        problems)


    def test_booking_problems_price_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SEC_USERNAME, password=BOOKING_SEC_PASSWORD)

        data = self.place_details.copy()
        data['account'] = str(acc1.id)
        data['created_0'] = '1970-01-01'
        data['created_1'] = '00:00:00'
        data['state'] = BOOKING_BOOKED
        data['amount_due'] = '0.00'
        data['price_type'] = PRICE_FULL
        resp = self.client.post(reverse('cciw.bookings.views.booking_problems_json'),
                                data)

        json = simplejson.loads(resp.content)
        problems = json['problems']
        p_full = Price.objects.get(price_type=PRICE_FULL, year=get_thisyear())
        self.assertTrue(any(p.startswith(u"The 'amount due' is not the expected value of £%s"
                                         % p_full.price)
                            for p in problems))


    def test_booking_problems_deposit_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SEC_USERNAME, password=BOOKING_SEC_PASSWORD)

        data = self.place_details.copy()
        data['account'] = str(acc1.id)
        data['created_0'] = '1970-01-01'
        data['created_1'] = '00:00:00'
        data['state'] = BOOKING_CANCELLED
        data['amount_due'] = '0.00'
        data['price_type'] = PRICE_FULL
        resp = self.client.post(reverse('cciw.bookings.views.booking_problems_json'),
                                data)

        json = simplejson.loads(resp.content)
        problems = json['problems']
        p_deposit = Price.objects.get(price_type=PRICE_DEPOSIT, year=get_thisyear())
        self.assertTrue(any(p.startswith(u"The 'amount due' is not the expected value of £%s"
                                         % p_deposit.price)
                            for p in problems))

        # Check 'full refund' cancellation.
        data['state'] = BOOKING_CANCELLED_FULL_REFUND
        data['amount_due'] = '20.00'
        data['price_type'] = PRICE_FULL
        resp = self.client.post(reverse('cciw.bookings.views.booking_problems_json'),
                                data)

        json = simplejson.loads(resp.content)
        problems = json['problems']
        self.assertTrue(any(p.startswith(u"The 'amount due' is not the expected value of £0.00")
                            for p in problems))


class TestAccountOverview(CreatePlaceMixin, TestCase):

    fixtures = ['basic.json']

    url = reverse('cciw.bookings.views.account_overview')

    def test_show(self):
        self.login()

        acc = self.get_account()

        # Book a place and pay
        self.create_place()
        book_basket_now(acc.bookings.basket(self.camp.year))
        acc.receive_payment(acc.bookings.all()[0].amount_due)

        # Book another
        self.create_place({'first_name': 'Another',
                           'last_name': 'Child'})
        book_basket_now(acc.bookings.basket(self.camp.year))

        # 3rd place, not booked at all
        self.create_place({'first_name': '3rd',
                           'last_name': 'child'})

        # 4th place, cancelled
        self.create_place({'first_name': '4th',
                           'last_name': 'child'})
        b = acc.bookings.get(first_name='4th', last_name='child')
        b.state = BOOKING_CANCELLED
        b.auto_set_amount_due()
        b.save()

        resp = self.client.get(self.url)

        # Another one, so that messages are cleared
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        # Confirmed place
        self.assertContains(resp, self.place_details['first_name'])


        # Booked place
        self.assertContains(resp, 'Another Child')
        self.assertContains(resp, 'remember to pay')

        # Basket/Shelf
        self.assertContains(resp, 'items in your basket')

        # Deposit for cancellation
        self.assertContains(resp, u"Cancelled")
        self.assertContains(resp, u"(£20 deposit)")


class TestLogOut(LogInMixin, TestCase):

    fixtures = ['basic']

    url = reverse('cciw.bookings.views.logout')

    def test_get(self):
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        self.login()
        resp = self.client.post(self.url, {'logout': '1'})
        self.assertEqual(resp.status_code, 302)

        # Try accessing a page which is restricted
        resp2 = self.client.get(reverse('cciw.bookings.views.account_overview'))
        self.assertEqual(resp2.status_code, 302)


class TestExpireBookingsCommand(CreatePlaceMixin, TestCase):

    fixtures = ['basic']

    def test_just_created(self):
        """
        Test no mail if just created
        """
        self.login()
        self.create_place()

        acc = self.get_account()
        book_basket_now(acc.bookings.basket(get_thisyear()))

        mail.outbox = []

        ExpireBookingsCommand().handle()
        self.assertEqual(len(mail.outbox), 0)

    def test_warning(self):
        """
        Test that we get a warning email after 12 hours
        """
        self.login()
        self.create_place()

        acc = self.get_account()
        book_basket_now(acc.bookings.basket(get_thisyear()))
        b = acc.bookings.all()[0]
        b.booking_expires = b.booking_expires - timedelta(0.49)
        b.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("warning" in mail.outbox[0].subject)

        b = acc.bookings.all()[0]
        self.assertNotEqual(b.booking_expires, None)
        self.assertEqual(b.state, BOOKING_BOOKED)

    def test_expires(self):
        """
        Test that we get an expiry email after 24 hours
        """
        self.login()
        self.create_place()

        acc = self.get_account()
        book_basket_now(acc.bookings.basket(get_thisyear()))
        b = acc.bookings.all()[0]
        b.booking_expires = b.booking_expires - timedelta(1.01)
        b.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        # NB - should get one, not two (shouldn't get warning)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("expired" in mail.outbox[0].subject)
        self.assertTrue("have expired" in mail.outbox[0].body)

        b = acc.bookings.all()[0]
        self.assertEqual(b.booking_expires, None)
        self.assertEqual(b.state, BOOKING_INFO_COMPLETE)

    def test_grouping(self):
        """
        Test the emails are grouped as we expect
        """
        self.login()
        self.create_place({'first_name':'Child',
                           'last_name': 'One'})
        self.create_place({'first_name':'Child',
                           'last_name': 'Two'})

        acc = self.get_account()
        book_basket_now(acc.bookings.basket(get_thisyear()))
        acc.bookings.update(booking_expires = datetime.now() - timedelta(1))

        mail.outbox = []
        ExpireBookingsCommand().handle()

        # Should get one, not two, because they will be grouped.
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("expired" in mail.outbox[0].subject)
        self.assertTrue("have expired" in mail.outbox[0].body)
        self.assertTrue("Child One" in mail.outbox[0].body)
        self.assertTrue("Child Two" in mail.outbox[0].body)

        for b in acc.bookings.all():
            self.assertEqual(b.booking_expires, None)
            self.assertEqual(b.state, BOOKING_INFO_COMPLETE)


class TestChequePayment(TestCase):

    def test_create(self):
        acc = BookingAccount.objects.create(email='foo@foo.com')
        self.assertEqual(Payment.objects.count(), 0)
        ChequePayment.objects.create(account=acc,
                                     amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, Decimal('100.00'))

    def test_delete(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = ChequePayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))
        Payment.objects.all().delete() # reset

        # Test
        cp.delete()
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, -cp.amount)

    def test_edit(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = ChequePayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))

        cp.amount=Decimal("101.00")
        self.assertRaises(Exception, cp.save)


class TestRefundPayment(TestCase):

    def test_create(self):
        acc = BookingAccount.objects.create(email='foo@foo.com')
        self.assertEqual(Payment.objects.count(), 0)
        RefundPayment.objects.create(account=acc,
                                     amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, Decimal('-100.00'))

    def test_delete(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = RefundPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))
        Payment.objects.all().delete() # reset

        # Test
        cp.delete()
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, cp.amount)

    def test_edit(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = RefundPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))

        cp.amount=Decimal("101.00")
        self.assertRaises(Exception, cp.save)



class TestCancel(CreatePlaceMixin, TestCase):
    """
    Tests covering what happens when a user cancels.
    """
    fixtures = ['basic.json']

    def test_amount_due(self):
        self.create_place()
        acc = self.get_account()
        place = acc.bookings.all()[0]
        place.state = BOOKING_CANCELLED
        self.assertEqual(place.expected_amount_due(), Price.objects.get(price_type=PRICE_DEPOSIT).price)

    def test_account_amount_due(self):
        self.create_place()
        acc = self.get_account()
        place = acc.bookings.all()[0]
        place.state = BOOKING_CANCELLED
        place.auto_set_amount_due()
        place.save()

        acc = self.get_account()
        self.assertEqual(acc.get_balance(), place.amount_due)


class TestCancelFullRefund(CreatePlaceMixin, TestCase):
    """
    Tests covering what happens when CCIW cancels a camp,
    using 'full refund'.
    """
    fixtures = ['basic.json']

    def test_amount_due(self):
        self.create_place()
        acc = self.get_account()
        place = acc.bookings.all()[0]
        place.state = BOOKING_CANCELLED_FULL_REFUND
        self.assertEqual(place.expected_amount_due(), Decimal('0.00'))

    def test_account_amount_due(self):
        self.create_place()
        acc = self.get_account()
        place = acc.bookings.all()[0]
        place.state = BOOKING_CANCELLED_FULL_REFUND
        place.auto_set_amount_due()
        place.save()

        acc = self.get_account()
        self.assertEqual(acc.get_balance(), place.amount_due)
