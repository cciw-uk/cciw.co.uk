import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

import pytest
import vcr
import xlrd
from django.conf import settings
from django.core import mail, signing
from django.db import models
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django_functest import FuncBaseMixin, Upload
from hypothesis import example, given
from hypothesis import strategies as st

from cciw.bookings.email import EmailVerifyTokenGenerator, VerifyExpired, VerifyFailed, send_payment_reminder_emails
from cciw.bookings.hooks import paypal_payment_received, unrecognised_payment
from cciw.bookings.mailchimp import get_status
from cciw.bookings.management.commands.expire_bookings import Command as ExpireBookingsCommand
from cciw.bookings.middleware import BOOKING_COOKIE_SALT
from cciw.bookings.models import (
    AccountTransferPayment,
    AgreementFetcher,
    Booking,
    BookingAccount,
    BookingState,
    ManualPayment,
    ManualPaymentType,
    Payment,
    PaymentSource,
    Price,
    PriceChecker,
    PriceType,
    RefundPayment,
    book_basket_now,
    build_paypal_custom_field,
    expire_bookings,
)
from cciw.bookings.utils import camp_bookings_to_spreadsheet, payments_to_spreadsheet
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camps_factories
from cciw.cciwmain.tests.mailhelpers import path_and_query_to_url, read_email_url
from cciw.mail.tests import send_queued_mail
from cciw.officers.tests import factories as officers_factories
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.spreadsheet import ExcelFormatter
from cciw.utils.tests.base import AtomicChecksMixin, TestBase, disable_logging
from cciw.utils.tests.db import refresh
from cciw.utils.tests.factories import Auto
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase

from . import factories


class IpnMock:
    payment_status = "Completed"
    business = settings.PAYPAL_RECEIVER_EMAIL


# == Mixins to reduce duplication ==


class BookingLogInMixin:
    booker_email = "booker@bookers.com"

    def booking_login(self, add_account_details=True, shortcut=None) -> BookingAccount:
        if getattr(self, "_logged_in", False):
            return

        if shortcut is None:
            shortcut = self.is_full_browser_test

        if shortcut:
            account, _ = BookingAccount.objects.get_or_create(email=self.booker_email)
            self._set_signed_cookie("bookingaccount", account.id, salt=BOOKING_COOKIE_SALT)
        else:
            # Easiest way is to simulate what the user actually has to do
            self.get_url("cciw-bookings-start")
            self.fill_by_name({"email": self.booker_email})
            self.submit("[type=submit]")
            url, path, querydata = read_email_url(mail.outbox.pop(), "https://.*/booking/v/.*")
            self.get_literal_url(path_and_query_to_url(path, querydata))
            account = BookingAccount.objects.get(email=self.booker_email)

        if add_account_details:
            account.name = "Joe"
            account.address_line1 = "456 My Street"
            account.address_city = "Metrocity"
            account.address_country = "GB"
            account.address_post_code = "XYZ"
            account.phone_number = "0123 456789"
            account.save()
        self._logged_in = True
        return account

    def _set_signed_cookie(self, key, value, salt=""):
        value = signing.get_cookie_signer(salt=key + salt).sign(value)
        if self.is_full_browser_test:
            if not self._have_visited_page():
                self.get_url("django_functest.emptypage")
            return self._driver.add_cookie({"name": key, "value": value, "path": "/"})
        else:
            return self.app.set_cookie(key, value)


class CreateBookingWebMixin(BookingLogInMixin):
    """
    Mixin to be used for functional testing of creating bookings online. It
    creates `self.camp` and `self.camp_2` and provides other utility methods.
    """

    today = date(2020, 2, 1)

    # For other, model level tests, we prefer explicit use of factories
    # for the things under test.

    def setUp(self):
        super().setUp()
        self.create_camps()

    camp_minimum_age = 11
    camp_maximum_age = 17

    def create_camps(self):
        if hasattr(self, "camp"):
            return
        # Need to create a Camp that we can choose i.e. is in the future.
        # We also need it so that payments can be made when only the deposit is due
        delta_days = 20 + settings.BOOKING_FULL_PAYMENT_DUE.days
        start_date = self.today + timedelta(delta_days)
        self.camp = camps_factories.create_camp(
            camp_name="Blue",
            minimum_age=self.camp_minimum_age,
            maximum_age=self.camp_maximum_age,
            start_date=start_date,
        )
        self.camp_2 = camps_factories.create_camp(
            camp_name="Red",
            minimum_age=self.camp_minimum_age,
            maximum_age=self.camp_maximum_age,
            start_date=start_date + timedelta(days=7),
        )

    def add_prices(self, deposit=Auto, early_bird_discount=Auto):
        if hasattr(self, "price_full"):
            return
        year = self.camp.year
        (
            self.price_full,
            self.price_2nd_child,
            self.price_3rd_child,
            self.price_deposit,
            self.price_early_bird_discount,
        ) = factories.create_prices(year, deposit=deposit, early_bird_discount=early_bird_discount)

    def create_booking(
        self,
        shortcut: bool = Auto,
        camp: Camp = Auto,
        first_name: str = Auto,
        last_name: str = Auto,
        name: str = Auto,
        sex="m",
        date_of_birth: date = Auto,
        serious_illness: bool = False,
        price_type=PriceType.FULL,
    ) -> Booking:
        """
        Creates a booking, normally using views.
        """
        if shortcut is Auto:
            # To speed up full browser test, we create booking using the shortcut
            shortcut = self.is_full_browser_test

        # DWIM - we always want prices to existing if we call 'create_booking()'
        self.add_prices()
        data = self.get_place_details(
            camp=camp,
            first_name=first_name,
            last_name=last_name,
            name=name,
            sex=sex,
            date_of_birth=date_of_birth,
            price_type=price_type,
            serious_illness=serious_illness,
        )
        if shortcut:
            data.update(
                {
                    "account": BookingAccount.objects.get(email=self.booker_email),
                    "state": BookingState.INFO_COMPLETE,
                }
            )
            return factories.create_booking(**data)

        # Normally we use public views to create place, to ensure that they
        # are created in the same way that a user would.
        old_booking_ids = list(Booking.objects.values_list("id", flat=True))

        self.get_url("cciw-bookings-add_place")
        # Sanity check:
        self.assertTextPresent("Please enter the details needed to book a place on a camp")
        self.fill_by_name(data)
        self.submit("#id_save_btn")
        self.assertUrlsEqual(reverse("cciw-bookings-list_bookings"))
        new_booking = Booking.objects.exclude(id__in=old_booking_ids).get()
        return new_booking

    def get_place_details(
        self,
        *,
        first_name: str = Auto,
        last_name: str = Auto,
        name: str = Auto,
        camp: Camp = Auto,
        date_of_birth: date = Auto,
        serious_illness: bool = False,
        price_type=PriceType.FULL,
        sex="m",
    ) -> dict:

        if name is not Auto:
            assert first_name is Auto
            assert last_name is Auto
            first_name, last_name = name.split(" ")
        else:
            first_name = first_name or "Frédéric"
            last_name = last_name or "Bloggs"
        if camp is Auto:
            camp = self.camp
        if date_of_birth is Auto:
            date_of_birth = date(camp.year - 14, 1, 1)
        if sex is Auto:
            sex = "m"
        return {
            # Order follows order in form.
            "camp": camp,
            "price_type": price_type,
            "first_name": first_name,
            "last_name": last_name,
            "sex": sex,
            "date_of_birth": date_of_birth,
            "address_line1": "123 My street",
            "address_city": "Metrocity",
            "address_country": "GB",
            "address_post_code": "ABC 123",
            "contact_name": "Mr Father",
            "contact_line1": "98 Main Street",
            "contact_city": "Metrocity",
            "contact_country": "GB",
            "contact_post_code": "ABC 456",
            "contact_phone_number": "01982 987654",
            "gp_name": "Doctor Who",
            "gp_line1": "The Tardis",
            "gp_city": "London",
            "gp_country": "GB",
            "gp_post_code": "SW1 1PQ",
            "gp_phone_number": "01234 456789",
            "medical_card_number": "asdfasdf",
            "last_tetanus_injection_date": date(camp.year - 5, 2, 3),
            "serious_illness": serious_illness,
            "agreement": True,
        }

    def fill(self, data, scroll=True):
        # Accept more things than super().fill()
        # This allows us to write `get_place_details()` above in a way
        # that means that data can be easily passed to Factory.create_booking()
        data2 = {}
        for k, v in data.items():
            if isinstance(v, models.Model):
                # Allow using Camp instances
                data2[k] = v.id
            elif isinstance(v, date):
                data2[k] = v.isoformat()
            else:
                data2[k] = v
        return super().fill(data2, scroll=scroll)


class BookingBaseMixin(AtomicChecksMixin):

    # Constants used in 'assertTextPresent' and 'assertTextAbsent', the latter
    # being prone to false positives if a constant isn't used.
    ABOVE_MAXIMUM_AGE = "above the maximum age"
    BELOW_MINIMUM_AGE = "below the minimum age"
    CAMP_CLOSED_FOR_BOOKINGS = "This camp is closed for bookings"
    CANNOT_USE_2ND_CHILD = "You cannot use a 2nd child discount"
    CANNOT_USE_MULTIPLE_DISCOUNT_FOR_ONE_CAMPER = "only one place may use a 2nd/3rd child discount"
    MULTIPLE_2ND_CHILD_WARNING = "You have multiple places at '2nd child"
    MULTIPLE_FULL_PRICE_WARNING = "You have multiple places at 'Full price"
    NOT_ENOUGH_PLACES = "There are not enough places left on this camp"
    NOT_ENOUGH_PLACES_FOR_BOYS = "There are not enough places for boys left on this camp"
    NOT_ENOUGH_PLACES_FOR_GIRLS = "There are not enough places for girls left on this camp"
    NO_PLACES_LEFT = "There are no places left on this camp"
    NO_PLACES_LEFT_FOR_BOYS = "There are no places left for boys"
    NO_PLACES_LEFT_FOR_GIRLS = "There are no places left for girls"
    PRICES_NOT_SET = "prices have not been set"
    LAST_TETANUS_INJECTION_DATE_REQUIRED = "last tetanus injection"
    BOOKINGS_WILL_EXPIRE = "you have 24 hours to complete payment online"
    THANK_YOU_FOR_PAYMENT = "Thank you for your payment"

    def setUp(self):
        super().setUp()
        HtmlChunk.objects.get_or_create(name="bookingform_post_to", menu_link=None)
        HtmlChunk.objects.get_or_create(name="booking_secretary_address", menu_link=None)


# == Test cases ==

# Most tests are against views, instead of model-based tests.
# Booking.get_booking_problems(), for instance, is tested especially in
# TestListBookings. In theory this could be tested using model-based tests
# instead, but the way that multiple bookings and the basket/shelf interact mean
# we need to test the view code as well. It would probably be good to rewrite
# using a class like "CheckoutPage", which combines shelf and basket bookings,
# and some of the logic in BookingListBookings. There is also the advantage that
# using self.create_booking() (which uses a view) ensures Booking instances are
# created the same way a user would.


class TestBookingModels(AtomicChecksMixin, TestBase):
    def test_camp_open_for_bookings(self):
        today = date.today()
        camp = camps_factories.create_camp(start_date=today + timedelta(days=10))
        assert camp.open_for_bookings(today)
        assert camp.open_for_bookings(camp.start_date)
        assert not camp.open_for_bookings(camp.start_date + timedelta(days=1))

        camp.last_booking_date = today
        assert camp.open_for_bookings(today)
        assert not camp.open_for_bookings(today + timedelta(days=1))

    @mock.patch("cciw.bookings.models.early_bird_is_available", return_value=False)
    def test_book_with_money_in_account(self, m, use_prefetch_related_for_get_account=True):
        booking = factories.create_booking(camp=camps_factories.create_camp(future=True))

        # Put some money in the account - just the deposit price will do.
        account = booking.account
        account.receive_payment(PriceChecker().get_deposit_price(booking.camp.year))
        account.save()

        # Book
        book_basket_now([booking])

        # Place should be booked AND should not expire
        booking.refresh_from_db()
        assert booking.state == BookingState.BOOKED
        assert booking.booking_expires is None

        # balance should be zero
        price_checker = PriceChecker()
        price_checker._fetch_prices(booking.camp.year)  # Force evaluation to check for zero queries later.

        for use_prefetch_related_for_get_account in [True, False]:
            if use_prefetch_related_for_get_account:
                # Tests that the other code paths in get_balance/BookingManager.payable
                # work.
                account = BookingAccount.objects.filter(id=account.id).prefetch_related("bookings")[0]
            else:
                account = BookingAccount.objects.get(id=account.id)
            with self.assertNumQueries(0 if use_prefetch_related_for_get_account else 2):
                assert account.get_balance(
                    confirmed_only=False,
                    allow_deposits=True,
                    price_checker=price_checker,
                ) == Decimal("0.00")
                assert account.get_balance(
                    confirmed_only=True,
                    allow_deposits=True,
                    price_checker=price_checker,
                ) == Decimal("0.00")

        # But for full amount, they still owe 80 (full price minus deposit)
        assert account.get_balance_full() == Decimal("80.00")

        # Test some model methods:
        assert len(account.bookings.payable(confirmed_only=False)) == 1

    def test_booking_missing_agreements(self):
        camp = camps_factories.create_camp(future=True)
        booking = factories.create_booking(state=BookingState.BOOKED, camp=camp)
        agreement = factories.create_custom_agreement(year=booking.camp.year, name="test")
        # Other agreement, different year so should be irrelevant:
        factories.create_custom_agreement(year=booking.camp.year - 1, name="x")
        assert booking in Booking.objects.agreement_fix_required()
        assert booking not in Booking.objects.no_missing_agreements()
        assert booking.get_missing_agreements() == [agreement]

        booking.custom_agreements_checked = [agreement.id]
        booking.save()

        assert booking not in Booking.objects.agreement_fix_required()
        assert booking not in Booking.objects.missing_agreements()
        assert booking in Booking.objects.no_missing_agreements()
        assert booking.get_missing_agreements() == []

    def test_get_missing_agreements_performance(self):
        # We can use common AgreementFetcher with get_missing_agreements to get
        # good performance:
        bookings = []
        camp = camps_factories.get_any_camp()
        for i in range(0, 20):
            bookings.append(factories.create_booking(camp=camp))
        agreement = factories.create_custom_agreement(year=camp.year, name="test")
        agreement_fetcher = AgreementFetcher()
        with self.assertNumQueries(2):
            bookings = Booking.objects.filter(id__in=[booking.id for booking in bookings]).select_related("camp")
            for booking in bookings:
                assert booking.get_missing_agreements(agreement_fetcher=agreement_fetcher) == [agreement]


class TestBookingIndex(BookingBaseMixin, WebTestBase):
    def test_show_with_no_prices(self):
        camp = camps_factories.create_camp()
        self.get_url("cciw-bookings-index")
        self.assertTextPresent(f"Prices for {camp.year} have not been finalised yet")

    def test_show_with_prices(self):
        camp = camps_factories.create_camp()
        factories.create_prices(camp.year, full_price=100, deposit=20)
        self.get_url("cciw-bookings-index")
        self.assertTextPresent("£100")
        self.assertTextPresent("£20")


class BookingStartBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = "cciw-bookings-start"

    def submit(self, css_selector="[type=submit]"):
        return super().submit(css_selector)

    def test_show_form(self):
        self.get_url(self.urlname)
        self.assertTextPresent("id_email")

    def test_complete_form(self):
        assert BookingAccount.objects.all().count() == 0
        self.get_url(self.urlname)
        self.fill_by_name({"email": "booker@bookers.com"})
        self.submit()
        assert BookingAccount.objects.all().count() == 0
        assert len(mail.outbox) == 1

    def test_complete_form_existing_email(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        assert BookingAccount.objects.all().count() == 1
        self.get_url(self.urlname)
        self.fill_by_name({"email": "booker@bookers.com"})
        self.submit()
        assert BookingAccount.objects.all().count() == 1
        assert len(mail.outbox) == 1

    def test_complete_form_existing_email_different_case(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        assert BookingAccount.objects.all().count() == 1
        self.get_url(self.urlname)
        self.fill_by_name({"email": "BOOKER@bookers.com"})
        self.submit()
        assert BookingAccount.objects.all().count() == 1
        assert len(mail.outbox) == 1

    def test_skip_if_logged_in(self):
        # This assumes verification process works
        # Check redirect to step 3 - account details
        self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-account_details"))

    def test_skip_if_account_details(self):
        # Check redirect to step 4 - add place
        self.booking_login()
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-add_place"))

    def test_skip_if_has_place_details(self):
        # Check redirect to overview
        account = self.booking_login()
        factories.create_booking(account=account)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-account_overview"))


class TestBookingStartWT(BookingStartBase, WebTestBase):
    pass


class TestBookingStartSL(BookingStartBase, SeleniumBase):
    pass


class BookingVerifyBase(BookingBaseMixin, FuncBaseMixin):
    def submit(self, css_selector="[type=submit]"):
        return super().submit(css_selector)

    def _read_email_verify_email(self, email):
        return read_email_url(email, "https://.*/booking/v/.*")

    def _start(self, email="booker@bookers.com"):
        # Assumes booking_start works:
        self.get_url("cciw-bookings-start")
        self.fill_by_name({"email": email})
        self.submit()

    def test_verify_correct(self):
        """
        Test the email verification stage when the URL is correct
        """
        self._start(email="booker@bookers.com")
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse("cciw-bookings-account_details"))
        self.assertTextPresent("Logged in as booker@bookers.com! You will stay logged in for two weeks")
        account = BookingAccount.objects.get(email="booker@bookers.com")
        assert account.last_login is not None
        assert account.first_login is not None

    def _add_booking_account_address(self, email="booker@bookers.com"):
        account, _ = BookingAccount.objects.get_or_create(email=email)
        account.name = "Joe"
        account.address_line1 = "Home"
        account.address_city = "My city"
        account.address_country = "GB"
        account.address_post_code = "XY1 D45"
        account.save()

    def test_verify_correct_and_has_details(self):
        """
        Test the email verification stage when the URL is correct and the
        account already has name and address
        """
        self._start()
        self._add_booking_account_address()
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse("cciw-bookings-add_place"))

    def test_verify_correct_and_has_old_details(self):
        """
        Test the email verification stage when the URL is correct and the
        account already has name and address, but they haven't logged in
        for 'a while'.
        """
        self._start()
        self._add_booking_account_address()
        account = BookingAccount.objects.get(email="booker@bookers.com")
        account.first_login = timezone.now() - timedelta(30 * 7)
        account.last_login = account.first_login
        account.save()

        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse("cciw-bookings-account_details"))
        self.assertTextPresent("Welcome back!")
        self.assertTextPresent("Please check and update your account details")

    def test_verify_incorrect(self):
        """
        Test the email verification stage when the URL is incorrect
        """
        self._start()

        # The following will trigger a BadSignature
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata["bt"] = "a000" + querydata["bt"]
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed", within="title")

        # This will trigger a base64 decode error:
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata["bt"] = "XXX" + querydata["bt"]
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed", within="title")

        # This will trigger a UnicodeDecodeError
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata["bt"] = "xxxx"
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed", within="title")


class TestBookingVerifyWT(BookingVerifyBase, WebTestBase):
    pass


class TestBookingVerifySL(BookingVerifyBase, SeleniumBase):
    pass


class TestPaymentReminderEmails(BookingBaseMixin, WebTestBase):
    def _create_booking(self):
        booking = factories.create_booking()
        book_basket_now([booking])
        booking = Booking.objects.get(id=booking.id)
        booking.confirm()
        assert len(BookingAccount.objects.payments_due()) == 1
        return booking

    def test_payment_reminder_email(self):
        booking = self._create_booking()
        mail.outbox = []
        send_payment_reminder_emails()
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "You have payments due" in m.body
        assert "[CCIW] Payment due" == m.subject
        url, path, querydata = read_email_url(m, "https://.*/booking/p.*")
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse("cciw-bookings-pay"))
        self.assertTextPresent(booking.account.get_balance_due_now(price_checker=PriceChecker()))

    def test_payment_reminder_email_link_expired(self):
        self._create_booking()
        mail.outbox = []
        send_payment_reminder_emails()
        m = mail.outbox[0]
        url, path, querydata = read_email_url(m, "https://.*/booking/p.*")

        with override_settings(BOOKING_EMAIL_VERIFY_TIMEOUT=timedelta(days=-1)):
            self.get_literal_url(path_and_query_to_url(path, querydata))

        # link expired, new email should be sent.
        self.assertUrlsEqual(reverse("cciw-bookings-link_expired_email_sent"))
        assert len(mail.outbox) == 2
        m2 = mail.outbox[1]

        url2, path2, querydata2 = read_email_url(m2, "https://.*/booking/p.*")
        self.get_literal_url(path_and_query_to_url(path2, querydata2))
        self.assertUrlsEqual(reverse("cciw-bookings-pay"))


class AccountDetailsBase(BookingBaseMixin, BookingLogInMixin, FuncBaseMixin):

    urlname = "cciw-bookings-account_details"
    submit_css_selector = "[type=submit]"

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-not_logged_in"))

    def test_show_if_logged_in(self):
        self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse(self.urlname))

    def test_missing_name(self):
        self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    @mock.patch("cciw.bookings.mailchimp.update_newsletter_subscription")
    def test_complete(self, UNS_func):
        """
        Test that we can complete the account details page
        """
        account = self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.submit()
        account.refresh_from_db()
        assert account.name == "Mr Booker"
        assert UNS_func.call_count == 0

    @mock.patch("cciw.bookings.mailchimp.update_newsletter_subscription")
    def test_news_letter_subscribe(self, UNS_func):
        account = self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.fill({"#id_subscribe_to_newsletter": True})
        self.submit()
        account.refresh_from_db()
        assert account.subscribe_to_newsletter
        assert UNS_func.call_count == 1

    def test_subscribe_to_mailings_unselected(self):
        account = self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        #  Initial value should be NULL - we haven't asked.
        assert account.subscribe_to_mailings is None
        assert account.include_in_mailings is True
        self._fill_in_account_details()
        self.submit()
        account.refresh_from_db()
        # The form should default to 'False'. As soon as this
        # page has been submitted, we *have* asked the question
        # and they have said 'no' by not selecting the box.
        assert account.subscribe_to_mailings is False
        assert account.include_in_mailings is False

    def test_subscribe_to_mailings_selected(self):
        account = self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.fill({"#id_subscribe_to_mailings": True})
        self.submit()
        account.refresh_from_db()
        assert account.subscribe_to_mailings is True
        assert account.include_in_mailings is True

    def _fill_in_account_details(self):
        self.fill_by_name(
            {
                "name": "Mr Booker",
                "address_line1": "123, A Street",
                "address_city": "Metrocity",
                "address_country": "GB",
                "address_post_code": "XY1 D45",
            }
        )

    # For updating this, see:
    # https://vcrpy.readthedocs.org/en/latest/usage.html

    @vcr.use_cassette("cciw/bookings/fixtures/vcr_cassettes/subscribe.yaml", ignore_localhost=True)
    def test_subscribe(self):
        account = self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.fill_by_name({"subscribe_to_newsletter": True})
        self.submit()
        account.refresh_from_db()
        assert account.subscribe_to_newsletter
        assert get_status(account) == "subscribed"

    @vcr.use_cassette("cciw/bookings/fixtures/vcr_cassettes/unsubscribe.yaml", ignore_localhost=True)
    def test_unsubscribe(self):
        account = self.booking_login()
        account.subscribe_to_newsletter = True
        account.save()

        self.get_url(self.urlname)
        self.fill_by_name({"subscribe_to_newsletter": False})
        self.submit()
        account.refresh_from_db()
        assert not account.subscribe_to_newsletter
        assert get_status(account) == "unsubscribed"


class TestAccountDetailsWT(AccountDetailsBase, WebTestBase):
    pass


class TestAccountDetailsSL(AccountDetailsBase, SeleniumBase):
    pass


class AddPlaceBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = "cciw-bookings-add_place"

    SAVE_BTN = "#id_save_btn"

    submit_css_selector = SAVE_BTN

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-not_logged_in"))

    def test_redirect_if_no_account_details(self):
        self.booking_login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-account_details"))

    def test_show_if_logged_in(self):
        self.booking_login()
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse(self.urlname))

    def test_show_error_if_no_prices(self):
        self.booking_login()
        self.get_url(self.urlname)
        self.assertTextPresent(self.PRICES_NOT_SET)

    def test_post_not_allowed_if_no_prices(self):
        self.booking_login()
        self.get_url(self.urlname)
        assert not self.is_element_present(self.SAVE_BTN)

        self.add_prices()
        self.get_url(self.urlname)
        data = self.get_place_details()
        self.fill_by_name(data)
        # Now remove prices, just to be awkward:
        Price.objects.all().delete()
        self.submit()
        self.assertTextPresent(self.PRICES_NOT_SET)

    def test_allowed_if_prices_set(self):
        self.booking_login()
        self.add_prices()
        self.get_url(self.urlname)
        self.assertTextAbsent(self.PRICES_NOT_SET)

    def test_incomplete(self):
        self.booking_login()
        self.add_prices()
        self.get_url(self.urlname)
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    def test_complete(self):
        account = self.booking_login()
        self.add_prices()
        self.get_url(self.urlname)
        assert account.bookings.count() == 0
        data = self.get_place_details()
        self.fill_by_name(data)
        self.submit()
        self.assertUrlsEqual(reverse("cciw-bookings-list_bookings"))

        # Did we create it?
        assert account.bookings.count() == 1

        booking = account.bookings.get()

        # Check attributes set correctly
        assert booking.amount_due == self.price_full
        assert booking.created_online
        assert not booking.publicity_photos_agreement

    def test_custom_agreement(self):
        agreement = factories.create_custom_agreement(
            name=(agreement_name := "MONEY!!"),
            year=self.camp.year,
            text_html=(agreement_text := "Do you agree to give us all your money?"),
        )
        account = self.booking_login()
        self.add_prices()
        self.get_url(self.urlname)
        self.assertTextPresent(agreement_name)
        self.assertTextPresent(agreement_text)

        self.fill_by_name(self.get_place_details())
        self.fill({f"#id_custom_agreement_{agreement.id}": True})
        self.submit()
        self.assertUrlsEqual(reverse("cciw-bookings-list_bookings"))

        booking = account.bookings.get()
        assert booking.custom_agreements_checked == [agreement.id]


class TestAddPlaceWT(AddPlaceBase, WebTestBase):
    pass


class TestAddPlaceSL(AddPlaceBase, SeleniumBase):
    def _use_existing_start(self):
        self.booking_login()
        self.create_booking(shortcut=True)
        self.get_url(self.urlname)

    def assertValues(self, data):
        for k, v in data.items():
            assert self.value(k) == v

    def test_use_existing_addresses(self):
        self._use_existing_start()

        self.click(".use_existing_btn")
        self.click("#id_use_address_btn")

        self.assertValues(
            {
                "#id_address_line1": "123 My street",
                "#id_address_country": "GB",
                "#id_address_post_code": "ABC 123",
                "#id_contact_name": "Mr Father",
                "#id_contact_line1": "98 Main Street",
                "#id_contact_country": "GB",
                "#id_contact_post_code": "ABC 456",
                "#id_first_name": "",
                "#id_gp_name": "",
                "#id_gp_line1": "",
                "#id_gp_country": "GB",
            }
        )

    def test_use_existing_gp(self):
        self._use_existing_start()

        self.click(".use_existing_btn")
        self.click("#id_use_gp_info_btn")

        self.assertValues(
            {
                "#id_address_line1": "",
                "#id_address_country": "GB",
                "#id_address_post_code": "",
                "#id_contact_name": "",
                "#id_contact_line1": "",
                "#id_contact_country": "GB",
                "#id_contact_post_code": "",
                "#id_first_name": "",
                "#id_gp_name": "Doctor Who",
                "#id_gp_line1": "The Tardis",
                "#id_gp_country": "GB",
            }
        )

    def test_use_existing_all(self):
        self._use_existing_start()

        self.click(".use_existing_btn")
        self.click("#id_use_all_btn")

        self.assertValues(
            {
                "#id_address_line1": "123 My street",
                "#id_address_country": "GB",
                "#id_address_post_code": "ABC 123",
                "#id_contact_name": "Mr Father",
                "#id_contact_line1": "98 Main Street",
                "#id_contact_country": "GB",
                "#id_contact_post_code": "ABC 456",
                "#id_first_name": "Frédéric",
                "#id_gp_name": "Doctor Who",
                "#id_gp_line1": "The Tardis",
                "#id_gp_country": "GB",
            }
        )

    def test_use_account_data(self):
        self._use_existing_start()

        self.click("#id_use_account_1_btn")
        self.assertValues(
            {
                "#id_address_line1": "456 My Street",
                "#id_address_city": "Metrocity",
                "#id_address_country": "GB",
                "#id_phone_number": "0123 456789",
                "#id_address_post_code": "XYZ",
            }
        )

        self.click("#id_use_account_2_btn")
        self.assertValues(
            {
                "#id_contact_line1": "456 My Street",
                "#id_contact_name": "Joe",
                "#id_contact_city": "Metrocity",
                "#id_contact_country": "GB",
                "#id_contact_phone_number": "0123 456789",
                "#id_contact_post_code": "XYZ",
            }
        )


class EditPlaceBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    # Most functionality is shared with the 'add' form, so doesn't need testing separately.

    submit_css_selector = "#id_save_btn"

    def edit_place(self, booking, expect_code=None):
        url = reverse("cciw-bookings-edit_place", kwargs={"booking_id": str(booking.id)})
        expect_errors = expect_code is not None and str(expect_code).startswith("4")
        action = lambda: self.get_literal_url(url, expect_errors=expect_errors)
        if expect_errors:
            with disable_logging():  # suppress django.request warning
                action()
        else:
            action()
        if expect_code is not None:
            self.assertCode(expect_code)

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url("cciw-bookings-edit_place", booking_id="1")
        self.assertUrlsEqual(reverse("cciw-bookings-not_logged_in"))

    def test_show_if_owner(self):
        self.booking_login()
        booking = self.create_booking()
        self.edit_place(booking)
        self.assertTextPresent("id_save_btn")

    def test_404_if_not_owner(self):
        self.booking_login()
        booking = self.create_booking()
        other_account = factories.create_booking_account()
        Booking.objects.all().update(account=other_account)
        self.edit_place(booking, expect_code=404)
        self.assertTextPresent("Page Not Found")

    def test_incomplete(self):
        self.booking_login()
        booking = self.create_booking()
        self.edit_place(booking)
        self.fill_by_name({"first_name": ""})
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    def test_complete(self):
        self.booking_login()
        booking = self.create_booking()
        self.edit_place(booking)
        data = self.get_place_details()
        data["first_name"] = "A New Name"
        self.fill_by_name(data)
        self.submit()
        self.assertUrlsEqual(reverse("cciw-bookings-list_bookings"))

        # Did we alter it?
        booking.refresh_from_db()
        assert booking.first_name == "A New Name"

    def test_edit_booked(self):
        """
        Test we can't edit a booking when it is already booked.
        (or anything but BookingState.INFO_COMPLETE)
        """
        account = self.booking_login()
        self.create_booking()
        b = account.bookings.get()

        for state in [BookingState.APPROVED, BookingState.BOOKED]:
            b.state = state
            b.save()

            # Check there is no save button
            self.edit_place(b)
            assert not self.is_element_present("#id_save_btn")
            # Check for message
            self.assertTextPresent("can only be changed by an admin.")

            # Attempt a post.

            # First, load a page with a working submit button:
            b.state = BookingState.INFO_COMPLETE
            b.save()
            self.edit_place(b)

            # Now change behind the scenes:
            b.state = state
            b.save()

            # Now submit
            data = self.get_place_details()
            data["first_name"] = "A New Name"
            self.fill_by_name(data)
            self.submit()
            # Check we didn't alter it
            assert account.bookings.get().first_name != "A New Name"


class TestEditPlaceWT(EditPlaceBase, WebTestBase):
    pass


class TestEditPlaceSL(EditPlaceBase, SeleniumBase):
    pass


def fix_autocomplete_fields(field_names):
    class FixAutocompleteFieldMixin:
        def fill_by_name(self, fields):
            new_fields = {}
            to_fix = []
            for field_name, value in fields.items():
                if field_name in field_names:
                    if self.is_full_browser_test:
                        # Fix later
                        to_fix.append((field_name, value))
                    else:
                        # Hack needed to cope with autocomplete widget and WebTest:
                        form, field, item = self._find_form_and_field_by_css_selector(
                            self.last_response,
                            f"[name={field_name}]",
                        )
                        # Modify the select widget so that it has the value we need
                        form.fields[field_name][0].options.append((str(value), False, ""))
                        new_fields[field_name] = value
                else:
                    new_fields[field_name] = value

            super().fill_by_name(new_fields)

            if self.is_full_browser_test:
                for field_name, value in to_fix:
                    # Hack to cope with autocomplete widget and Selenium
                    self.execute_script(
                        f"""django.jQuery('[name={field_name}]').append('<option value="{value}" selected="selected"></option>');"""
                    )

    return FixAutocompleteFieldMixin


class EditPlaceAdminBase(BookingBaseMixin, fix_autocomplete_fields(["account"]), CreateBookingWebMixin, FuncBaseMixin):
    def test_approve(self):
        self.booking_login()
        booking = self.create_booking(price_type=PriceType.CUSTOM)

        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_booking_change", booking.id)
        self.fill_by_name({"state": BookingState.APPROVED})
        self.submit("[name=_save]")
        self.assertTextPresent("An email has been sent")
        mails = send_queued_mail()
        assert len(mails) == 1

    def test_create(self):
        self.add_prices()
        self.officer_login(officers_factories.create_booking_secretary())
        account = BookingAccount.objects.create(
            email=self.booker_email,
            name="Joe",
            address_post_code="XYZ",
        )
        self.get_url("admin:bookings_booking_add")
        fields = self.get_place_details()
        fields.update(
            {
                "account": account.id,
                "state": BookingState.BOOKED,
                "amount_due": "130.00",
                "manual_payment_amount": "100",
                "manual_payment_payment_type": str(ManualPaymentType.CHEQUE),
            }
        )
        self.fill_by_name(fields)
        self.submit("[name=_save]")
        self.assertTextPresent("Select booking")
        self.assertTextPresent("A confirmation email has been sent")
        booking = Booking.objects.get()
        assert not booking.created_online
        assert booking.account.manual_payments.count() == 1
        mp = booking.account.manual_payments.get()
        assert mp.payment_type == ManualPaymentType.CHEQUE
        assert mp.amount == Decimal("100")


class TestEditPlaceAdminWT(EditPlaceAdminBase, WebTestBase):
    pass


class TestEditPlaceAdminSL(EditPlaceAdminBase, SeleniumBase):
    pass


class EditAccountAdminBase(BookingBaseMixin, FuncBaseMixin):
    def test_create(self):
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_bookingaccount_add")
        self.fill_by_name(
            {
                "name": "Joe",
                "email": "joe@example.com",
                "address_post_code": "XYZ",
            }
        )
        self.submit("[name=_save]")
        self.assertTextPresent("was added successfully")
        account = BookingAccount.objects.get(email="joe@example.com")
        assert account.name == "Joe"

    def test_edit(self):
        account = factories.create_booking_account(name="Joe")
        account.manual_payments.create(
            amount=Decimal("10.00"),
            payment_type=ManualPaymentType.CHEQUE,
        )
        assert account.payments.count() == 1
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_bookingaccount_change", account.id)
        self.assertTextPresent("Payments")
        self.assertTextPresent("Payment: 10.00 from Joe via Cheque")
        self.fill_by_name({"name": "Mr New Name"})
        self.submit("[name=_save]")
        self.assertTextPresent("was changed successfully")
        account = refresh(account)
        assert account.name == "Mr New Name"


class TestEditAccountAdminWT(EditAccountAdminBase, WebTestBase):
    pass


class TestEditAccountAdminSL(EditAccountAdminBase, SeleniumBase):
    pass


class EditPaymentAdminBase(fix_autocomplete_fields(["account"]), BookingBaseMixin, FuncBaseMixin):
    def test_add_manual_payment(self):
        booking = factories.create_booking()
        self.officer_login(officers_factories.create_booking_secretary())
        account = booking.account
        self.get_url("admin:bookings_manualpayment_add")
        self.fill_by_name(
            {
                "account": account.id,
                "amount": "12.00",
            }
        )
        self.submit("[name=_save]")
        self.assertTextPresent("Manual payment of £12")
        self.assertTextPresent("was added successfully")
        account.refresh_from_db()
        assert account.manual_payments.count() == 1
        assert account.total_received == Decimal("12")


class TestEditPaymentAdminWT(EditPaymentAdminBase, WebTestBase):
    pass


class TestEditPaymentAdminSL(EditPaymentAdminBase, SeleniumBase):
    pass


class AccountTransferBase(fix_autocomplete_fields(["from_account", "to_account"]), AtomicChecksMixin, FuncBaseMixin):
    def test_add_account_transfer(self):

        account_1 = BookingAccount.objects.create(email="account1@example.com", name="Joe")
        account_2 = BookingAccount.objects.create(email="account2@example.com", name="Jane")
        account_1.manual_payments.create(amount="100.00")
        account_1 = refresh(account_1)
        assert account_1.total_received == Decimal("100.00")

        assert account_1.payments.count() == 1

        self.officer_login(officers_factories.create_booking_secretary())

        self.get_url("admin:bookings_accounttransferpayment_add")
        self.fill_by_name(
            {
                "from_account": account_1.id,
                "to_account": account_2.id,
                "amount": "15",
            }
        )
        self.submit("[name=_save]")
        self.assertTextPresent("was added successfully")

        account_1 = refresh(account_1)
        account_2 = refresh(account_2)

        assert account_1.payments.count() == 2
        assert account_2.payments.count() == 1

        assert account_1.total_received == Decimal("85.00")
        assert account_2.total_received == Decimal("15.00")

        # Deleting causes more payments to restore the original value
        account_1.transfer_from_payments.get().delete()

        account_1 = refresh(account_1)
        account_2 = refresh(account_2)

        assert account_1.payments.count() == 3
        assert account_2.payments.count() == 2

        assert account_1.total_received == Decimal("100.00")
        assert account_2.total_received == Decimal("0.00")


class TestAccountTransferWT(AccountTransferBase, WebTestBase):
    pass


class TestAccountTransferSL(AccountTransferBase, SeleniumBase):
    pass


class ListBookingsBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):
    # This includes tests for most of the business logic

    urlname = "cciw-bookings-list_bookings"

    def assert_book_button_enabled(self):
        assert self.is_element_present("#id_book_now_btn")
        assert not self.is_element_present("#id_book_now_btn[disabled]")

    def assert_book_button_disabled(self):
        assert self.is_element_present("#id_book_now_btn")
        assert self.is_element_present("#id_book_now_btn[disabled]")

    def enable_book_button(self):
        # Used for testing what happens if user enables button using browser
        # tools etc. i.e. checking that we have proper server side validation
        if self.is_full_browser_test:
            self.execute_script("""$('#id_book_now_btn').removeAttr('disabled')""")

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse("cciw-bookings-not_logged_in"))

    def test_show_bookings(self):
        self.booking_login()
        self.create_booking("Frédéric Bloggs")
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("£100")
        self.assertTextPresent("This place can be booked")
        self.assert_book_button_enabled()

    def test_handle_custom_price(self):
        self.booking_login()
        self.create_booking(price_type=PriceType.CUSTOM)
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("TBA")
        self.assertTextPresent("A custom discount needs to be arranged by the booking secretary")
        self.assert_book_button_disabled()
        self.assertTextPresent("This place cannot be booked for the reasons described above")

    def test_2nd_child_discount_allowed(self):
        self.booking_login()
        self.create_booking(price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

        # 2 places, both at 2nd child discount, is not allowed.
        self.create_booking(price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

    def test_2nd_child_discount_allowed_if_booked(self):
        """
        Test that we can have 2nd child discount if full price
        place is already booked.
        """
        account = self.booking_login()
        self.create_booking(first_name="Joe")
        account.bookings.update(state=BookingState.BOOKED)

        self.create_booking(first_name="Mary", price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assert_book_button_enabled()

    def test_3rd_child_discount_allowed(self):
        self.booking_login()
        self.create_booking(price_type=PriceType.FULL)
        self.create_booking(price_type=PriceType.THIRD_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent("You cannot use a 3rd child discount")
        self.assert_book_button_disabled()

        # 3 places, with 2 at 3rd child discount, is not allowed.
        self.create_booking(price_type=PriceType.THIRD_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent("You cannot use a 3rd child discount")
        self.assert_book_button_disabled()

    def test_handle_serious_illness(self):
        self.booking_login()
        booking = self.create_booking(serious_illness=True)
        self.get_url(self.urlname)
        self.assertTextPresent("Must be approved by leader due to serious illness/condition")
        self.assert_book_button_disabled()
        assert booking in Booking.objects.need_approving()

    def test_minimum_age(self):
        # if born Aug 31st 2001, and thisyear == 2012, should be allowed on camp with
        # minimum_age == 11
        self.booking_login()
        self.create_booking(date_of_birth="%d-08-31" % (self.camp.year - self.camp_minimum_age))
        self.get_url(self.urlname)
        self.assertTextAbsent(self.BELOW_MINIMUM_AGE)

        # if born 1st Sept 2001, and thisyear == 2012, should not be allowed on camp with
        # minimum_age == 11
        Booking.objects.all().delete()
        self.create_booking(date_of_birth="%d-09-01" % (self.camp.year - self.camp_minimum_age))
        self.get_url(self.urlname)
        self.assertTextPresent(self.BELOW_MINIMUM_AGE)

    def test_maximum_age(self):
        # if born 1st Sept 2001, and thisyear == 2019, should be allowed on camp with
        # maximum_age == 17
        self.booking_login()
        self.create_booking(date_of_birth="%d-09-01" % (self.camp.year - (self.camp_maximum_age + 1)))
        self.get_url(self.urlname)
        self.assertTextAbsent(self.ABOVE_MAXIMUM_AGE)

        # if born Aug 31st 2001, and thisyear == 2019, should not be allowed on camp with
        # maximum_age == 17
        Booking.objects.all().delete()
        self.create_booking(date_of_birth="%d-08-31" % (self.camp.year - (self.camp_maximum_age + 1)))
        self.get_url(self.urlname)
        self.assertTextPresent(self.ABOVE_MAXIMUM_AGE)

    def test_no_places_left(self):
        for i in range(0, self.camp.max_campers):
            factories.create_booking(camp=self.camp, state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="m")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT)
        self.assert_book_button_disabled()

        # Don't want a redundant message
        self.assertTextAbsent(self.NO_PLACES_LEFT_FOR_BOYS)

    def test_no_male_places_left(self):
        for i in range(0, self.camp.max_male_campers):
            factories.create_booking(camp=self.camp, sex="m", state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="m")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT_FOR_BOYS)
        self.assert_book_button_disabled()

        # Check that we can still book female places
        Booking.objects.filter(state=BookingState.INFO_COMPLETE).delete()
        self.create_booking(sex="f")
        self.get_url(self.urlname)
        self.assertTextAbsent(self.NO_PLACES_LEFT)
        self.assert_book_button_enabled()

    def test_no_female_places_left(self):
        for i in range(0, self.camp.max_female_campers):
            factories.create_booking(camp=self.camp, sex="f", state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="f")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT_FOR_GIRLS)
        self.assert_book_button_disabled()

    def test_not_enough_places_left(self):
        for i in range(0, self.camp.max_campers - 1):
            factories.create_booking(camp=self.camp, sex="m", state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="f")
        self.create_booking(sex="f")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES)
        self.assert_book_button_disabled()

    def test_not_enough_male_places_left(self):
        for i in range(0, self.camp.max_male_campers - 1):
            factories.create_booking(camp=self.camp, sex="m", state=BookingState.BOOKED)
        self.camp.bookings.update(state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="m")
        self.create_booking(sex="m")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES_FOR_BOYS)
        self.assert_book_button_disabled()

    def test_not_enough_female_places_left(self):
        for i in range(0, self.camp.max_female_campers - 1):
            factories.create_booking(camp=self.camp, sex="f", state=BookingState.BOOKED)
        self.camp.bookings.update(state=BookingState.BOOKED)

        self.booking_login()
        self.create_booking(sex="f")
        self.create_booking(sex="f")
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES_FOR_GIRLS)
        self.assert_book_button_disabled()

    def test_booking_after_closing_date(self):
        self.camp.last_booking_date = self.today - timedelta(days=1)
        self.camp.save()

        self.booking_login()
        self.create_booking()
        self.get_url(self.urlname)
        self.assertTextPresent(self.CAMP_CLOSED_FOR_BOOKINGS)
        self.assert_book_button_disabled()

    def test_handle_two_problem_bookings(self):
        # Test the error we get for more than one problem booking
        self.booking_login()
        self.create_booking(
            name="Frédéric Bloggs",
            price_type=PriceType.CUSTOM,
        )
        self.create_booking(name="Another Child", price_type=PriceType.CUSTOM)
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("TBA")
        self.assertTextPresent("A custom discount needs to be arranged by the booking secretary")
        self.assert_book_button_disabled()
        self.assertTextPresent("These places cannot be booked for the reasons described above")

    def test_handle_mixed_problem_and_non_problem(self):
        # Test the message we get if one place is bookable and the other is not
        self.booking_login()
        self.create_booking()  # bookable
        self.create_booking(name="Another Child", price_type=PriceType.CUSTOM)  # not bookable
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.assertTextPresent("One or more of the places cannot be booked")

    def test_total(self):
        self.booking_login()
        self.create_booking()
        self.create_booking()
        self.get_url(self.urlname)
        self.assertTextPresent("£200")

    def test_manually_approved(self):
        # manually approved places should appear as OK to book
        self.booking_login()
        self.create_booking(name="Frédéric Bloggs")  # bookable
        booking2 = self.create_booking(name="Another Child", price_type=PriceType.CUSTOM)
        Booking.objects.filter(id=booking2.id).update(state=BookingState.APPROVED, amount_due=Decimal("0.01"))
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("£100")
        self.assertTextPresent("This place can be booked")

        self.assertTextPresent("Another Child")
        self.assertTextPresent("£0.01")

        self.assert_book_button_enabled()
        # Total:
        self.assertTextPresent("£100.01")

    def test_add_another_btn(self):
        self.booking_login()
        self.create_booking()
        self.get_url(self.urlname)
        self.submit("[name=add_another]")
        self.assertUrlsEqual(reverse("cciw-bookings-add_place"))

    def test_move_to_shelf(self):
        self.booking_login()
        booking = self.create_booking()
        assert not booking.shelved
        self.get_url(self.urlname)

        self.submit(f"[name=shelve_{booking.id}]")

        # Should be changed
        booking.refresh_from_db()
        assert booking.shelved

        # Different button should appear
        assert not self.is_element_present(f"[name=shelve_{booking.id}]")
        assert self.is_element_present(f"[name=unshelve_{booking.id}]")

        self.assertTextPresent("Shelf")

    def test_move_to_basket(self):
        self.booking_login()
        booking = self.create_booking()
        booking.shelved = True
        booking.save()

        self.get_url(self.urlname)
        self.submit(f"[name=unshelve_{booking.id}]")

        # Should be changed
        booking.refresh_from_db()
        assert not booking.shelved

        # Shelf section should disappear.
        self.assertTextAbsent("Shelf")

    def test_delete_place(self):
        account = self.booking_login()
        booking = self.create_booking()
        self.get_url(self.urlname)

        if self.is_full_browser_test:
            self.click(f"[name=delete_{booking.id}]", expect_alert=True)
            self.accept_alert()
            self.wait_until_loaded("body")
        else:
            self.submit(f"[name=delete_{booking.id}]")

        # Should be gone
        if self.is_full_browser_test:
            self.wait_until(lambda d: account.bookings.count() == 0)
        else:
            assert account.bookings.count() == 0

    def test_edit_place_btn(self):
        self.booking_login()
        booking = self.create_booking()
        self.get_url(self.urlname)

        self.submit(f"[name=edit_{booking.id}]")
        self.assertUrlsEqual(reverse("cciw-bookings-edit_place", kwargs={"booking_id": booking.id}))

    def test_book_ok(self):
        """
        Test that we can book a place
        """
        self.booking_login()
        booking = self.create_booking()
        self.get_url(self.urlname)
        self.submit("[name=book_now]")
        booking.refresh_from_db()
        assert booking.state == BookingState.BOOKED
        assert not booking.is_confirmed
        self.assertUrlsEqual(reverse("cciw-bookings-pay"))
        self.assertTextPresent(self.BOOKINGS_WILL_EXPIRE)

    def test_book_with_zero_deposit(self):
        """
        Test that when deposit is zero, we confirm the place
        immediately and don't ask for payment.
        """
        self.add_prices(deposit=0)
        account = self.booking_login()
        booking = self.create_booking()
        self.get_url(self.urlname)
        self.submit("[name=book_now]")
        booking.refresh_from_db()
        assert booking.state == BookingState.BOOKED
        assert booking.is_confirmed
        self.assertUrlsEqual(reverse("cciw-bookings-pay"))
        self.assertTextAbsent(self.BOOKINGS_WILL_EXPIRE)
        self.assertTextPresent("no deposit to pay")
        self.assertTextPresent("do not pay yet")

        # We should immediately send email confirming place in this case:
        mails = send_queued_mail()
        assert len(mails) == 1
        (mail,) = mails
        assert mail.subject == "[CCIW] Booking - place confirmed"
        assert mail.to == [account.email]
        assert self.THANK_YOU_FOR_PAYMENT not in mail.body  # They didn't actually pay

    def test_book_with_other_bookings(self):
        """
        Test that when we have other bookings which are not "booked",
        distribute_balance doesn't fail.
        """
        self.add_prices(deposit=0)  # Zero deposit to allow confirmation without payment
        self.booking_login()

        def make_booking(state):
            booking = self.create_booking(shortcut=True)
            booking.state = state
            booking.save()
            return booking

        make_booking(BookingState.CANCELLED_FULL_REFUND)
        make_booking(BookingState.CANCELLED_HALF_REFUND)
        make_booking(BookingState.INFO_COMPLETE)

        booking = self.create_booking(shortcut=True)
        self.get_url(self.urlname)
        self.submit("[name=book_now]")
        booking.refresh_from_db()
        assert booking.state == BookingState.BOOKED
        assert booking.is_confirmed
        self.assertUrlsEqual(reverse("cciw-bookings-pay"))

    def test_book_unbookable(self):
        """
        Test that an unbookable place can't be booked
        """
        self.booking_login()
        booking = self.create_booking(serious_illness=True)
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.enable_book_button()
        self.submit("[name=book_now]")
        booking.refresh_from_db()
        assert booking.state == BookingState.INFO_COMPLETE
        self.assertTextPresent("These places cannot be booked")

    def test_book_one_unbookable(self):
        """
        Test that if one places is unbookable, no place can be booked
        """
        account = self.booking_login()
        self.create_booking()
        self.create_booking(serious_illness=True)
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.enable_book_button()
        self.submit("[name=book_now]")
        for b in account.bookings.all():
            assert b.state == BookingState.INFO_COMPLETE
        self.assertTextPresent("These places cannot be booked")

    def test_same_name_same_camp(self):
        self.booking_login()
        self.create_booking()
        self.create_booking()  # Identical

        self.get_url(self.urlname)
        self.assertTextPresent("You have entered another set of place details for a camper called")
        # This is only a warning:
        self.assert_book_button_enabled()

    def test_warn_about_multiple_full_price(self):
        self.booking_login()
        self.create_booking(name="Frédéric Bloggs")
        self.create_booking(name="Mary Bloggs")

        self.get_url(self.urlname)
        self.assertTextPresent(self.MULTIPLE_FULL_PRICE_WARNING)
        self.assertTextPresent("If Mary Bloggs and Frédéric Bloggs")
        # This is only a warning:
        self.assert_book_button_enabled()

        # Check for more than 2
        self.create_booking(name="Peter Bloggs")
        self.get_url(self.urlname)
        self.assertTextPresent("If Mary Bloggs, Peter Bloggs and Frédéric Bloggs")

    def test_warn_about_multiple_2nd_child(self):
        self.booking_login()
        self.create_booking(name="Frédéric Bloggs")
        self.create_booking(name="Mary Bloggs", price_type=PriceType.SECOND_CHILD)
        self.create_booking(name="Peter Bloggs", price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent(self.MULTIPLE_2ND_CHILD_WARNING)
        self.assertTextPresent("If Peter Bloggs and Mary Bloggs")
        self.assertTextPresent("one is eligible")
        # This is only a warning:
        self.assert_book_button_enabled()

        self.create_booking(name="Zac Bloggs", price_type=PriceType.SECOND_CHILD)
        self.get_url(self.urlname)
        self.assertTextPresent("2 are eligible")

    def test_dont_warn_about_multiple_full_price_for_same_child(self):
        self.booking_login()
        self.create_booking()
        self.create_booking(camp=self.camp_2)

        self.get_url(self.urlname)
        self.assertTextAbsent(self.MULTIPLE_FULL_PRICE_WARNING)
        self.assert_book_button_enabled()

    def test_error_for_2nd_child_discount_for_same_camper(self):
        self.booking_login()
        self.create_booking()
        self.create_booking(camp=self.camp_2, price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

    def test_error_for_multiple_2nd_child_discount(self):
        self.booking_login()
        # Frederik x2
        self.create_booking(name="Peter Bloggs")
        self.create_booking(name="Peter Bloggs", camp=self.camp_2)

        # Mary x2
        self.create_booking(name="Mary Bloggs", price_type=PriceType.SECOND_CHILD)
        self.create_booking(name="Mary Bloggs", camp=self.camp_2, price_type=PriceType.SECOND_CHILD)

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_MULTIPLE_DISCOUNT_FOR_ONE_CAMPER)
        self.assert_book_button_disabled()

    def test_book_now_safeguard(self):
        self.booking_login()
        # It might be possible to alter the list of items in the basket in one
        # tab, and then press 'Book now' from an out-of-date representation of
        # the basket. We need a safeguard against this.

        # Must include at least id,price,camp choice for each booking
        booking = self.create_booking()
        self.get_url(self.urlname)

        # Now modify
        booking.refresh_from_db()
        booking.amount_due = Decimal("35.01")
        booking.save()

        self.submit("[name=book_now]")
        # Should not be modified
        booking.refresh_from_db()
        assert booking.state == BookingState.INFO_COMPLETE
        self.assertTextPresent("Places were not booked due to modifications made")

    def test_book_disallowed_if_missing_agreement(self):
        # Test that we cannot book a place if an agreement is missing
        account = self.booking_login()
        self.create_booking()
        self.get_url(self.urlname)

        # Suppose an agreement is added split second later by admin:
        # (test done this way to ensure we are not just relying
        # on a disabled book button)
        factories.create_custom_agreement(year=self.camp.year, name="COVID-19")

        self.submit("[name=book_now]")
        booking = account.bookings.get()
        assert booking.state != BookingState.BOOKED

        self.assertTextPresent('You need to confirm your agreement in section "COVID-19"')
        self.assert_book_button_disabled()


class TestListBookingsWT(ListBookingsBase, WebTestBase):
    pass


class TestListBookingsSL(ListBookingsBase, SeleniumBase):
    pass


class PayBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):
    def test_balance_empty(self):
        self.booking_login()
        self.add_prices()
        self.get_url("cciw-bookings-pay")
        self.assertTextPresent("£0.00")

    def test_balance_after_booking(self):
        self.add_prices(early_bird_discount=0)
        self.booking_login()
        booking1 = self.create_booking()
        booking2 = self.create_booking()
        book_basket_now([booking1, booking2])

        self.get_url("cciw-bookings-pay")

        # 2 deposits
        expected_price = 2 * self.price_deposit
        self.assertTextPresent(f"£{expected_price}")

        # Move forward to after the time when just deposits are allowed:
        Camp.objects.update(start_date=date.today() + timedelta(10))

        self.get_url("cciw-bookings-pay")

        # 2 full price
        expected_price = 2 * self.price_full
        self.assertTextPresent(f"£{expected_price}")

    def test_redirect_if_missing_agreements(self):
        self.booking_login()
        booking = self.create_booking(shortcut=True)
        book_basket_now([booking])
        factories.create_custom_agreement(year=self.camp.year, name="COVID-19")
        self.get_url("cciw-bookings-pay")
        self.assertUrlsEqual(reverse("cciw-bookings-account_overview"))
        self.assertTextPresent("There is an issue with your existing bookings")
        self.assertTextPresent("COVID-19")


class TestPayWT(PayBase, WebTestBase):
    pass


class TestPaySL(PayBase, SeleniumBase):
    pass


class TestPayReturnPoints(BookingBaseMixin, BookingLogInMixin, WebTestBase):
    def test_pay_done(self):
        self.booking_login()
        self.get_url("cciw-bookings-pay_done")
        self.assertTextPresent("Payment complete!")
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse("cciw-bookings-pay_done"), {})
        assert resp.status_code == 200

    def test_pay_cancelled(self):
        self.booking_login()
        self.get_url("cciw-bookings-pay_cancelled")
        self.assertTextPresent("Payment cancelled")
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse("cciw-bookings-pay_cancelled"), {})
        assert resp.status_code == 200


class TestPaymentReceived(BookingBaseMixin, TestBase):
    def test_receive_payment(self):
        # Late booking:
        Camp.objects.update(start_date=date.today() + timedelta(days=1))

        booking = factories.create_booking()
        (_, leader_1_user), (_, leader_2_user) = camps_factories.create_and_add_leaders(booking.camp, count=2)
        account = booking.account
        book_basket_now([booking])
        booking.refresh_from_db()
        assert booking.booking_expires is not None

        mail.outbox = []
        ManualPayment.objects.create(
            account=account,
            amount=booking.amount_due,
        )

        account.refresh_from_db()

        # Check we updated the account
        assert account.total_received == booking.amount_due
        assert account.total_received > 0  # sanity check

        # Check we updated the bookings
        booking.refresh_from_db()
        assert booking.booking_expires is None

        # Check for emails sent
        # 1 to account
        mails = send_queued_mail()
        account_mails = [m for m in mails if m.to == [account.email]]
        assert len(account_mails) == 1

        # This is a late booking, therefore there is also:
        # 1 to camp leaders altogether
        leader_emails = [m for m in mails if sorted(m.to) == sorted([leader_1_user.email, leader_2_user.email])]
        assert len(leader_emails) == 1
        assert leader_emails[0].subject.startswith("[CCIW] Late booking:")

    def test_insufficient_receive_payment(self):
        # Need to move into region where deposits are not allowed.
        Camp.objects.update(start_date=date.today() + timedelta(days=20))
        booking1 = factories.create_booking(name="Peter Bloggs")
        account = booking1.account
        booking2 = factories.create_booking(price_type=PriceType.SECOND_CHILD, name="Mary Bloggs", account=account)
        book_basket_now([booking1, booking2])
        booking1.refresh_from_db()
        assert booking1.booking_expires is not None

        assert booking1.amount_due > booking2.amount_due
        # Pay an amount between the two:
        p = (booking1.amount_due + booking2.amount_due) / 2
        account.receive_payment(p)

        # Check we updated the account
        assert account.total_received == p

        # Check we updated the one we had enough funds for
        booking2.refresh_from_db()
        assert booking2.booking_expires is None
        # but not the one which was too much.
        booking1.refresh_from_db()
        assert booking1.booking_expires is not None

        # We can rectify it with a payment of the rest
        account.receive_payment((booking1.amount_due + booking2.amount_due) - p)
        booking1.refresh_from_db()
        assert booking1.booking_expires is None

    def test_email_for_bad_payment_1(self):
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal("1.00")
        ipn_1.custom = "x"  # wrong format

        mail.outbox = []
        assert len(mail.outbox) == 0
        paypal_payment_received(ipn_1)

        assert len(mail.outbox) == 1
        assert "/admin/ipn/paypal" in mail.outbox[0].body
        assert "No associated account" in mail.outbox[0].body

    def test_email_for_bad_payment_2(self):
        account = BookingAccount(id=1234567)  # bad ID, not in DB
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal("1.00")
        ipn_1.custom = build_paypal_custom_field(account)

        mail.outbox = []
        assert len(mail.outbox) == 0
        paypal_payment_received(ipn_1)

        assert len(mail.outbox) == 1
        assert "/admin/ipn/paypal" in mail.outbox[0].body
        assert "No associated account" in mail.outbox[0].body

    def test_email_for_bad_payment_3(self):
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal("1.00")

        mail.outbox = []
        assert len(mail.outbox) == 0
        unrecognised_payment(ipn_1)

        assert len(mail.outbox) == 1
        assert "/admin/ipn/paypal" in mail.outbox[0].body
        assert "Invalid IPN" in mail.outbox[0].body

    def test_receive_payment_handler(self):
        # Use the actual signal handler, check the good path.
        account = factories.create_booking_account()
        assert account.total_received == Decimal(0)

        ipn_1 = factories.create_ipn(account)

        # Test for Payment objects
        assert Payment.objects.count() == 1
        assert Payment.objects.all()[0].amount == ipn_1.mc_gross

        # Test account updated
        account.refresh_from_db()
        assert account.total_received == ipn_1.mc_gross

        # Test refund is wired up
        ipn_2 = factories.create_ipn(
            account,
            parent_txn_id="1",
            txn_id="2",
            mc_gross=-1 * ipn_1.mc_gross,
            payment_status="Refunded",
        )

        assert Payment.objects.count() == 2
        assert Payment.objects.order_by("-created_at")[0].amount == ipn_2.mc_gross

        account.refresh_from_db()
        assert account.total_received == Decimal(0)

    def test_email_for_good_payment(self):
        booking = factories.create_booking(state=BookingState.INFO_COMPLETE)
        account = booking.account
        book_basket_now([booking])

        mail.outbox = []
        factories.create_ipn(account, mc_gross=booking.amount_due)

        mails = send_queued_mail()
        assert len(mails) == 1

        assert mails[0].subject == "[CCIW] Booking - place confirmed"
        assert mails[0].to == [account.email]
        assert self.THANK_YOU_FOR_PAYMENT in mails[0].body

    def test_only_one_email_for_multiple_places(self):
        booking1 = factories.create_booking(name="Princess Pearl")
        account = booking1.account
        booking2 = factories.create_booking(name="Another Child", account=account)

        book_basket_now([booking1, booking2])

        mail.outbox = []
        account.receive_payment(account.get_balance_full())

        mails = send_queued_mail()
        assert len(mails) == 1

        assert mails[0].subject == "[CCIW] Booking - place confirmed"
        assert mails[0].to == [account.email]
        assert "Princess Pearl" in mails[0].body
        assert "Another Child" in mails[0].body

    def test_concurrent_save(self):
        acc1 = BookingAccount.objects.create(email="foo@foo.com")
        acc2 = BookingAccount.objects.get(email="foo@foo.com")

        acc1.receive_payment(Decimal("100.00"))

        assert BookingAccount.objects.get(email="foo@foo.com").total_received == Decimal("100.00")

        acc2.save()  # this will have total_received = 0.00

        assert BookingAccount.objects.get(email="foo@foo.com").total_received == Decimal("100.00")

    def test_pending_payment_handling(self):
        # This test is story-style - checks the whole process
        # of handling pending payments.

        # Create a place

        booking = factories.create_booking()
        account = booking.account

        # Book it
        book_basket_now([booking])
        # Sanity check initial condition:
        mail.outbox = []
        booking.refresh_from_db()
        assert booking.booking_expires is not None

        # Send payment that doesn't complete immediately
        ipn_1 = factories.create_ipn(
            account,
            txn_id="8DX10782PJ789360R",
            mc_gross=Decimal("20.00"),
            payment_status="Pending",
            pending_reason="echeck",
        )

        # Money should not be counted as received
        account = refresh(account)
        assert account.total_received == Decimal("0.00")

        # Custom email sent:
        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "We have received a payment of £20.00 that is pending" in m.body
        assert "echeck" in m.body

        # Check that we can tell the account has pending payments
        # and how much.
        three_days_later = timezone.now() + timedelta(days=3)
        assert account.get_pending_payment_total(now=three_days_later) == Decimal("20.00")

        # But pending payments are considered abandoned after 3 months.
        three_months_later = three_days_later + timedelta(days=30 * 3)
        assert account.get_pending_payment_total(now=three_months_later) == Decimal("0.00")

        # Booking should not expire if they have pending payments against them.
        # This is the easiest way to handle this, we have no idea when the
        # payment will complete.
        mail.outbox = []
        expire_bookings(now=three_days_later)
        booking.refresh_from_db()
        assert booking.booking_expires is not None

        # Once confirmed payment comes in, we consider that there are no pending payments.

        # A different payment doesn't affect whether pending ones are completed:
        factories.create_ipn(
            account,
            txn_id="ABCDEF123",  # DIFFERENT txn_id
            mc_gross=Decimal("10.00"),
            payment_status="Completed",
        )
        account = refresh(account)
        assert account.total_received == Decimal("10.00")
        assert account.get_pending_payment_total(now=three_days_later) == Decimal("20.00")

        # But the same TXN id is recognised as cancelling the pending payment
        factories.create_ipn(
            account,
            txn_id=ipn_1.txn_id,  # SAME txn_id
            mc_gross=ipn_1.mc_gross,
            payment_status="Completed",
        )
        account = refresh(account)
        assert account.total_received == Decimal("30.00")
        assert account.get_pending_payment_total(now=three_days_later) == Decimal("0.00")


class TestAjaxViews(BookingBaseMixin, CreateBookingWebMixin, WebTestBase):
    # Basic tests to ensure that the views that serve AJAX return something
    # sensible.

    # NB use a mixture of WebTest and Django client tests

    def test_places_json(self):
        self.booking_login()
        self.create_booking()
        resp = self.get_url("cciw-bookings-places_json")
        j = json.loads(resp.content.decode("utf-8"))
        assert j["places"][0]["first_name"] == self.get_place_details()["first_name"]

    def test_places_json_with_exclusion(self):
        self.booking_login()
        booking = self.create_booking()
        resp = self.get_literal_url(reverse("cciw-bookings-places_json") + f"?exclude={booking.id}")
        j = json.loads(resp.content.decode("utf-8"))
        assert j["places"] == []

    def test_places_json_with_bad_exclusion(self):
        self.booking_login()
        resp = self.get_literal_url(reverse("cciw-bookings-places_json") + "?exclude=x")
        j = json.loads(resp.content.decode("utf-8"))
        assert j["places"] == []

    def test_account_json(self):
        account = self.booking_login()
        account.address_line1 = "123 Main Street"
        account.address_country = "FR"
        account.save()

        resp = self.get_url("cciw-bookings-account_json")
        j = json.loads(resp.content.decode("utf-8"))
        assert j["account"]["address_line1"] == "123 Main Street"
        assert j["account"]["address_country"] == "FR"

    def test_booking_account_json(self):
        acc1 = BookingAccount.objects.create(email="foo@foo.com", address_post_code="ABC", name="Mr Foo")

        self.officer_login(officers_factories.create_officer())
        resp = self.get_literal_url(reverse("cciw-officers-booking_account_json"), expect_errors=True)
        assert resp.status_code == 403

        # Now as booking secretary
        self.officer_login(officers_factories.create_booking_secretary())
        resp = self.get_literal_url(reverse("cciw-officers-booking_account_json") + f"?id={acc1.id}")
        assert resp.status_code == 200

        j = json.loads(resp.content.decode("utf-8"))
        assert j["account"]["address_post_code"] == "ABC"

    def _booking_problems_json(self, place_details):
        data = {}
        for k, v in place_details.items():
            data[k] = v.id if isinstance(v, models.Model) else v

        resp = self.client.post(reverse("cciw-officers-booking_problems_json"), data)
        return json.loads(resp.content.decode("utf-8"))

    def _initial_place_details(self):
        data = self.get_place_details()
        data["created_at_0"] = "1970-01-01"  # Simulate form, which doesn't supply created
        data["created_at_1"] = "00:00:00"
        return data

    def test_booking_problems(self):
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com", address_post_code="ABC", name="Mr Foo")
        officer = officers_factories.create_booking_secretary()
        self.client.force_login(officer)
        resp = self.client.post(reverse("cciw-officers-booking_problems_json"), {"account": str(acc1.id)})

        assert resp.status_code == 200
        j = json.loads(resp.content.decode("utf-8"))
        assert not j["valid"]

        data = self._initial_place_details()
        data["account"] = str(acc1.id)
        data["state"] = BookingState.APPROVED
        data["amount_due"] = "100.00"
        data["price_type"] = PriceType.CUSTOM
        j = self._booking_problems_json(data)
        assert j["valid"]
        assert "A custom discount needs to be arranged by the booking secretary" in j["problems"]

    def test_booking_problems_price_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com", address_post_code="ABC", name="Mr Foo")
        officer = officers_factories.create_booking_secretary()
        self.client.force_login(officer)

        data = self._initial_place_details()
        data["account"] = str(acc1.id)
        data["state"] = BookingState.BOOKED
        data["amount_due"] = "0.00"
        data["price_type"] = PriceType.FULL
        j = self._booking_problems_json(data)
        assert any(
            p.startswith(f"The 'amount due' is not the expected value of £{self.price_full}") for p in j["problems"]
        )

    def test_booking_problems_deposit_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com", address_post_code="ABC", name="Mr Foo")
        officer = officers_factories.create_booking_secretary()
        self.client.force_login(officer)

        data = self._initial_place_details()
        data["account"] = str(acc1.id)
        data["state"] = BookingState.CANCELLED_DEPOSIT_KEPT
        data["amount_due"] = "0.00"
        data["price_type"] = PriceType.FULL
        j = self._booking_problems_json(data)
        assert any(
            p.startswith(f"The 'amount due' is not the expected value of £{self.price_deposit}") for p in j["problems"]
        )

        # Check 'full refund' cancellation.
        data["state"] = BookingState.CANCELLED_FULL_REFUND
        data["amount_due"] = "20.00"
        data["price_type"] = PriceType.FULL
        j = self._booking_problems_json(data)
        assert any(p.startswith("The 'amount due' is not the expected value of £0.00") for p in j["problems"])

    def test_booking_problems_early_bird_check(self):
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com", address_post_code="ABC", name="Mr Foo")
        officer = officers_factories.create_booking_secretary()
        self.client.force_login(officer)
        data = self._initial_place_details()
        data["early_bird_discount"] = "1"
        data["account"] = str(acc1.id)
        data["state"] = BookingState.BOOKED
        data["amount_due"] = "90.00"
        j = self._booking_problems_json(data)
        assert "The early bird discount is only allowed for bookings created online." in j["problems"]


class AccountOverviewBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = "cciw-bookings-account_overview"

    def test_show(self):
        # Book a place and pay
        account = self.booking_login()
        booking1 = self.create_booking(name="Frédéric Bloggs")
        book_basket_now([booking1])
        account.receive_payment(self.price_deposit)

        # Book another
        booking2 = self.create_booking(name="Another Child")
        book_basket_now([booking2])

        # 3rd place, not booked at all
        self.create_booking(name="3rd Child")

        # 4th place, cancelled
        booking4 = self.create_booking(name="4th Child")
        booking4.state = BookingState.CANCELLED_DEPOSIT_KEPT
        booking4.auto_set_amount_due()
        booking4.save()

        self.get_url(self.urlname)

        # Another one, so that messages are cleared
        self.get_url(self.urlname)

        # Confirmed place
        self.assertTextPresent("Frédéric")

        # Booked place
        self.assertTextPresent("Another Child")
        self.assertTextPresent("will expire soon")

        # Basket/Shelf
        self.assertTextPresent("Basket / shelf")

        # Deposit for cancellation
        self.assertTextPresent("Cancelled places")
        self.assertTextPresent("£20")

    def test_bookings_with_missing_agreements(self):
        account = self.booking_login()
        booking1 = self.create_booking()
        booking2 = self.create_booking()
        booking3 = self.create_booking()
        book_basket_now([booking1, booking2, booking3])

        agreement = factories.create_custom_agreement(year=booking1.camp.year, name="COVID-19")

        assert account.bookings.agreement_fix_required().count() == 3
        self.get_url(self.urlname)

        assert self.is_element_present(f"#id_edit_booking_{booking1.id}")
        assert self.is_element_present(f"#id_edit_booking_{booking2.id}")

        assert self.is_element_present(f"#id_cancel_booking_{booking1.id}")
        assert self.is_element_present(f"#id_cancel_booking_{booking2.id}")

        self.assertTextPresent('you need to confirm your agreement in section "COVID-19"')

        # Cancel button for booking1
        self.submit(f"#id_cancel_booking_{booking1.id}")
        booking1.refresh_from_db()
        assert not booking1.is_booked
        assert booking1.shelved

        assert account.bookings.agreement_fix_required().count() == 2

        # booking1 buttons should now disappear
        assert not self.is_element_present(f"#id_edit_booking_{booking1.id}")
        assert not self.is_element_present(f"#id_cancel_booking_{booking1.id}")

        # Edit button for booking2
        # This is really a test for the edit booking page
        # - it needs to allow edits in this case, even though the
        #   place is already booked.
        self.submit(f"#id_edit_booking_{booking2.id}")
        self.assertUrlsEqual(reverse("cciw-bookings-edit_place", kwargs={"booking_id": booking2.id}))
        self.fill({f"#id_custom_agreement_{agreement.id}": True})
        self.submit(AddPlaceBase.SAVE_BTN)

        assert account.bookings.agreement_fix_required().count() == 1
        booking2.refresh_from_db()

        # This process should not have unbooked the booking:
        assert booking2.is_booked

        # We still have booking3 to sort out, we should be back at
        # account overview
        self.assertUrlsEqual(reverse("cciw-bookings-account_overview"))


class TestAccountOverviewWT(AccountOverviewBase, WebTestBase):
    pass


class TestAccountOverviewSL(AccountOverviewBase, SeleniumBase):
    pass


class LogOutBase(BookingBaseMixin, BookingLogInMixin, FuncBaseMixin):
    def test_logout(self):
        self.booking_login()
        self.get_url("cciw-bookings-account_overview")
        self.submit("[name=logout]")
        self.assertUrlsEqual(reverse("cciw-bookings-index"))

        # Try accessing a page which is restricted
        self.get_url("cciw-bookings-account_overview")
        self.assertUrlsEqual(reverse("cciw-bookings-not_logged_in"))


class TestLogOutWT(LogOutBase, WebTestBase):
    pass


class TestLogOutSL(LogOutBase, SeleniumBase):
    pass


class TestExpireBookingsCommand(TestBase):
    def test_just_created(self):
        """
        Test no mail if just created
        """
        booking = factories.create_booking()
        book_basket_now([booking])

        mail.outbox = []

        ExpireBookingsCommand().handle()
        assert len(mail.outbox) == 0

    def test_warning(self):
        """
        Test that we get a warning email after 12 hours
        """
        booking = factories.create_booking()
        book_basket_now([booking])
        booking.refresh_from_db()
        booking.booking_expires = booking.booking_expires - timedelta(0.49)
        booking.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        assert len(mail.outbox) == 1
        assert "warning" in mail.outbox[0].subject

        booking.refresh_from_db()
        assert booking.booking_expires is not None
        assert booking.state == BookingState.BOOKED

    def test_expires(self):
        """
        Test that we get an expiry email after 24 hours
        """
        booking = factories.create_booking()
        book_basket_now([booking])
        booking.refresh_from_db()
        booking.booking_expires = booking.booking_expires - timedelta(1.01)
        booking.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        # NB - should get one, not two (shouldn't get warning)
        assert len(mail.outbox) == 1
        assert "expired" in mail.outbox[0].subject
        assert "have expired" in mail.outbox[0].body

        booking.refresh_from_db()
        assert booking.booking_expires is None
        assert booking.state == BookingState.INFO_COMPLETE

    def test_grouping(self):
        """
        Test the emails are grouped as we expect
        """
        booking1 = factories.create_booking(name="Child One")
        account = booking1.account
        booking2 = factories.create_booking(name="Child Two", account=account)

        book_basket_now([booking1, booking2])
        account.bookings.update(booking_expires=timezone.now() - timedelta(1))

        mail.outbox = []
        ExpireBookingsCommand().handle()

        # Should get one, not two, because they will be grouped.
        assert len(mail.outbox) == 1
        assert "expired" in mail.outbox[0].subject
        assert "have expired" in mail.outbox[0].body
        assert "Child One" in mail.outbox[0].body
        assert "Child Two" in mail.outbox[0].body

        for b in account.bookings.all():
            assert b.booking_expires is None
            assert b.state == BookingState.INFO_COMPLETE


class TestManualPayment(TestBase):
    def test_create(self):
        account = BookingAccount.objects.create(email="foo@foo.com")
        assert Payment.objects.count() == 0
        ManualPayment.objects.create(account=account, amount=Decimal("100.00"))
        assert Payment.objects.count() == 1
        assert Payment.objects.all()[0].amount == Decimal("100.00")

        account = BookingAccount.objects.get(id=account.id)
        assert account.total_received == Decimal("100.00")

    def test_delete(self):
        # Setup
        account = BookingAccount.objects.create(email="foo@foo.com")
        cp = ManualPayment.objects.create(account=account, amount=Decimal("100.00"))
        assert Payment.objects.count() == 1

        # Test
        cp.delete()
        assert Payment.objects.count() == 2
        account = BookingAccount.objects.get(id=account.id)
        assert account.total_received == Decimal("0.00")

    def test_edit(self):
        # Setup
        account = BookingAccount.objects.create(email="foo@foo.com")
        cp = ManualPayment.objects.create(account=account, amount=Decimal("100.00"))

        cp.amount = Decimal("101.00")
        with pytest.raises(Exception):
            cp.save()


class TestRefundPayment(TestBase):
    def test_create(self):
        account = BookingAccount.objects.create(email="foo@foo.com")
        assert Payment.objects.count() == 0
        RefundPayment.objects.create(account=account, amount=Decimal("100.00"))
        assert Payment.objects.count() == 1
        assert Payment.objects.all()[0].amount == Decimal("-100.00")

        account = BookingAccount.objects.get(id=account.id)
        assert account.total_received == Decimal("-100.00")

    def test_delete(self):
        # Setup
        account = BookingAccount.objects.create(email="foo@foo.com")
        cp = RefundPayment.objects.create(account=account, amount=Decimal("100.00"))
        assert Payment.objects.count() == 1

        # Test
        cp.delete()
        assert Payment.objects.count() == 2
        account = BookingAccount.objects.get(id=account.id)
        assert account.total_received == Decimal("0.00")

    def test_edit(self):
        # Setup
        account = BookingAccount.objects.create(email="foo@foo.com")
        cp = RefundPayment.objects.create(account=account, amount=Decimal("100.00"))

        cp.amount = Decimal("101.00")
        with pytest.raises(Exception):
            cp.save()


class TestCancel(TestBase):
    """
    Tests covering what happens when a user cancels.
    """

    def test_amount_due(self):
        booking = factories.create_booking()
        booking.state = BookingState.CANCELLED_DEPOSIT_KEPT
        assert booking.expected_amount_due() == PriceChecker().get_deposit_price(booking.camp.year)

    def test_account_amount_due(self):
        booking = factories.create_booking()
        account = booking.account
        booking.state = BookingState.CANCELLED_DEPOSIT_KEPT
        booking.auto_set_amount_due()
        booking.save()

        account.refresh_from_db()
        assert account.get_balance_full() == booking.amount_due


class TestCancelFullRefund(TestBase):
    """
    Tests covering what happens when CCiW cancels a camp,
    using 'full refund'.
    """

    def test_amount_due(self):
        booking = factories.create_booking()
        booking.state = BookingState.CANCELLED_FULL_REFUND
        assert booking.expected_amount_due() == Decimal("0.00")

    def test_account_amount_due(self):
        booking = factories.create_booking()
        account = booking.account
        booking.state = BookingState.CANCELLED_FULL_REFUND
        booking.auto_set_amount_due()
        booking.save()

        account.refresh_from_db()
        assert account.get_balance_full() == booking.amount_due


class TestEarlyBird(TestBase):
    def test_expected_amount_due(self):
        booking = factories.create_booking()
        price_checker = PriceChecker()
        year = booking.camp.year
        assert booking.expected_amount_due() == price_checker.get_full_price(year)

        booking.early_bird_discount = True
        assert booking.expected_amount_due() == price_checker.get_full_price(
            year
        ) - price_checker.get_early_bird_discount(year)

    def test_book_basket_applies_discount(self):
        booking = factories.create_booking()
        year = booking.camp.year
        with mock.patch("cciw.bookings.models.get_early_bird_cutoff_date") as mock_f:
            # Cut off date definitely in the future
            mock_f.return_value = datetime(year + 10, 1, 1, tzinfo=timezone.get_default_timezone())
            book_basket_now([booking])
        booking.refresh_from_db()
        assert booking.early_bird_discount
        price_checker = PriceChecker()
        assert booking.amount_due == price_checker.get_full_price(year) - price_checker.get_early_bird_discount(year)
        return booking

    def test_book_basket_doesnt_apply_discount(self):
        booking = factories.create_booking()
        with mock.patch("cciw.bookings.models.get_early_bird_cutoff_date") as mock_f:
            # Cut off date definitely in the past
            mock_f.return_value = datetime(booking.camp.year - 10, 1, 1, tzinfo=timezone.get_default_timezone())
            book_basket_now([booking])
        booking.refresh_from_db()
        assert not booking.early_bird_discount
        assert booking.amount_due == PriceChecker().get_full_price(booking.camp.year)

    def test_expire(self):
        booking = self.test_book_basket_applies_discount()
        booking.expire()

        assert not booking.early_bird_discount
        # For the sake of 'list bookings' view, we need to display the
        # un-discounted price.
        assert booking.amount_due == PriceChecker().get_full_price(booking.camp.year)
        assert booking.booked_at is None

    def test_non_early_bird_booking_warning(self):
        booking = factories.create_booking()
        mail.outbox = []
        account = booking.account
        with mock.patch("cciw.bookings.models.get_early_bird_cutoff_date") as mock_f:
            mock_f.return_value = timezone.now() - timedelta(days=10)
            book_basket_now([booking])
            account.receive_payment(booking.amount_due)
        mails = [m for m in send_queued_mail() if m.to == [account.email]]
        assert len(mails) == 1
        assert "If you had booked earlier" in mails[0].body
        assert "£10" in mails[0].body


class TestExportPlaces(TestBase):
    def test_summary(self):
        booking = factories.create_booking()
        booking.state = BookingState.BOOKED
        booking.save()

        workbook = camp_bookings_to_spreadsheet(booking.camp, ExcelFormatter()).to_bytes()
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh_all = wkbk.sheet_by_index(0)

        assert wksh_all.cell(0, 0).value == "First name"
        assert wksh_all.cell(1, 0).value == booking.first_name

    def test_birthdays(self):
        camp = camps_factories.create_camp()
        bday = camp.start_date + timedelta(1)
        dob = bday.replace(bday.year - 12)
        booking = factories.create_booking(date_of_birth=dob, camp=camp, state=BookingState.BOOKED)

        workbook = camp_bookings_to_spreadsheet(booking.camp, ExcelFormatter()).to_bytes()
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh_bdays = wkbk.sheet_by_index(2)

        assert wksh_bdays.cell(0, 0).value == "First name"
        assert wksh_bdays.cell(1, 0).value == booking.first_name

        assert wksh_bdays.cell(0, 2).value == "Birthday"
        assert wksh_bdays.cell(1, 2).value == bday.strftime("%A %d %B")

        assert wksh_bdays.cell(0, 3).value == "Age"
        assert wksh_bdays.cell(1, 3).value == "12"


class TestExportPaymentData(TestBase):
    def test_export(self):
        account1 = BookingAccount.objects.create(name="Joe Bloggs", email="joe@foo.com")
        account2 = BookingAccount.objects.create(name="Mary Muddle", email="mary@foo.com")
        factories.create_ipn(account1, mc_gross=Decimal("10.00"))
        ManualPayment.objects.create(account=account1, amount=Decimal("11.50"))
        RefundPayment.objects.create(account=account1, amount=Decimal("0.25"))
        AccountTransferPayment.objects.create(from_account=account2, to_account=account1, amount=Decimal("100.00"))
        mp2 = ManualPayment.objects.create(account=account1, amount=Decimal("1.23"))
        mp2.delete()

        now = timezone.now()
        workbook = payments_to_spreadsheet(
            now - timedelta(days=3), now + timedelta(days=3), ExcelFormatter()
        ).to_bytes()

        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)
        data = [[c.value for c in r] for r in wksh.get_rows()]
        assert data[0] == ["Account name", "Account email", "Amount", "Date", "Type"]

        # Excel dates are a pain, so we ignore them
        data2 = [[c for i, c in enumerate(r) if i != 3] for r in data[1:]]
        assert ["Joe Bloggs", "joe@foo.com", 10.0, "PayPal"] in data2
        assert ["Joe Bloggs", "joe@foo.com", 11.5, "Cheque"] in data2
        assert ["Joe Bloggs", "joe@foo.com", -0.25, "Refund Cheque"] in data2
        assert ["Joe Bloggs", "joe@foo.com", 100.00, "Account transfer"] in data2

        assert ["Joe Bloggs", "joe@foo.com", 1.23, "ManualPayment (deleted)"] not in data2
        assert ["Joe Bloggs", "joe@foo.com", -1.23, "ManualPayment (deleted)"] not in data2


class TestBookingModel(TestBase):
    def test_need_approving(self):
        factories.create_booking()
        assert len(Booking.objects.need_approving()) == 0

        Booking.objects.update(serious_illness=True)
        assert len(Booking.objects.need_approving()) == 1

        Booking.objects.update(serious_illness=False)
        Booking.objects.update(date_of_birth=date(1980, 1, 1))
        assert len(Booking.objects.need_approving()) == 1

        assert Booking.objects.get().approval_reasons() == ["Too old"]


class TestPaymentModels(TestBase):
    def test_payment_source_save_bad(self):
        manual = factories.create_manual_payment()
        refund = factories.create_refund_payment()
        with pytest.raises(AssertionError):
            PaymentSource.objects.create(manual_payment=manual, refund_payment=refund)

    def test_payment_source_save_good(self):
        manual = factories.create_manual_payment()
        PaymentSource.objects.all().delete()
        p = PaymentSource.objects.create(manual_payment=manual)
        assert p.id is not None

    def test_write_off_debt_payment(self):
        account = factories.create_booking_account()
        factories.create_booking(account=account, state=BookingState.BOOKED)
        account.refresh_from_db()

        balance = account.get_balance_full()
        assert balance > 0

        factories.create_write_off_debt_payment(account=account, amount=balance)
        account.refresh_from_db()

        assert account.get_balance_full() == 0


class SupportingInformationAdminBase(fix_autocomplete_fields("booking"), FuncBaseMixin):
    def test_separate_supporting_information_admin(self):
        booking = factories.create_booking()
        information_type = factories.create_supporting_information_type("test")
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_supportinginformation_add")
        self.fill_by_name(
            {
                "booking": booking.id,
                "information_type": information_type.id,
                "from_name": "Zog",
                "from_email": "zog@example.com",
                "from_telephone": "1234 567890",
                "notes": "These are some notes",
                "document": Upload("hello.txt", b"Hello"),
            }
        )
        self.submit("[name=_continue]")
        self.assertTextPresent("was added successfully")
        supporting_information = booking.supporting_information_records.get()
        assert supporting_information.information_type == information_type
        assert supporting_information.from_name == "Zog"
        assert supporting_information.from_email == "zog@example.com"
        assert supporting_information.from_telephone == "1234 567890"
        assert supporting_information.notes == "These are some notes"
        doc = supporting_information.document
        assert doc.filename.endswith("hello.txt")  # functest limitation means we don't get exact name
        assert bytes(doc.content) == b"Hello"
        assert doc.size == 5
        assert doc.mimetype == "text/plain"

        # Save again, without upload, shouldn't clear the doc.
        self.fill_by_name({"from_name": "Zog2"})
        self.submit("[name=_continue]")
        self.assertTextPresent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.from_name == "Zog2"
        assert supporting_information.document is not None
        assert supporting_information.document.filename.endswith("hello.txt")

        # Test clear
        self.fill_by_name({"document-clear": True})
        self.submit("[name=_continue]")
        self.assertTextPresent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.document is None
        self.assertTextPresent("was changed successfully")

        # Saving without upload (or file initially attached) should be allowed
        self.fill_by_name({"from_name": "Zog3"})
        self.submit("[name=_continue]")
        self.assertTextPresent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.from_name == "Zog3"

    def test_invalid_form_with_new_upload(self):
        supporting_information = factories.create_supporting_information(document_filename="old.txt")
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_supportinginformation_change", object_id=supporting_information.id)
        self.fill_by_name(
            {
                "from_name": "",  # Invalid, should block save
                "document": Upload("new_doc.txt", b"Hello"),
            }
        )
        self.submit("[name=_continue]")
        self.assertTextAbsent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.document.filename == "old.txt"

    def test_invalid_form_with_clear_upload(self):
        supporting_information = factories.create_supporting_information(document_filename="old.txt")
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_supportinginformation_change", object_id=supporting_information.id)
        self.fill_by_name(
            {
                "from_name": "",  # Invalid, should block save
                "document-clear": True,
            }
        )
        self.submit("[name=_continue]")
        self.assertTextAbsent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.document is not None
        assert supporting_information.document.filename == "old.txt"

    def test_supporting_information_inline(self):
        booking = factories.create_booking()
        information_type = factories.create_supporting_information_type("test")
        self.officer_login(officers_factories.create_booking_secretary())
        self.get_url("admin:bookings_booking_change", booking.id)
        if self.is_full_browser_test:
            self.click("#supporting_information_records-group .collapse-toggle")
            self.click("#supporting_information_records-group .add-row a")
        else:
            self.add_admin_inline_form_to_page("supporting_information_records")
        self.fill_by_name(
            {
                f"supporting_information_records-0-{k}": v
                for k, v in {
                    "information_type": information_type.id,
                    "from_name": "Zog",
                    "document": Upload("hello.txt", b"Hello"),
                }.items()
            }
        )
        self.submit("[name=_continue]")
        supporting_information = booking.supporting_information_records.get()
        # For other fields tests are above, we care most about file upload, which is
        # trickiest
        doc = supporting_information.document
        assert bytes(doc.content) == b"Hello"

        # Test clear
        if self.is_full_browser_test:
            self.click("#supporting_information_records-group .collapse-toggle")
        self.fill_by_name({"supporting_information_records-0-document-clear": True})
        self.submit("[name=_continue]")
        self.assertTextPresent("was changed successfully")
        supporting_information.refresh_from_db()
        assert supporting_information.document is None


class SupportingInformationAdminWT(SupportingInformationAdminBase, WebTestBase):
    pass


class SupportingInformationAdminSL(SupportingInformationAdminBase, SeleniumBase):
    pass


class DocumentDownloadView(WebTestBase):
    def test_deny_normal_user(self):
        info = factories.create_supporting_information(document_filename="anything.txt")
        self.officer_login(officers_factories.create_officer())
        response = self.get_literal_url(info.document.url, expect_errors=True)
        assert response.status_code == 404

    def test_allow_for_authorised_user(self):
        info = factories.create_supporting_information(
            document_filename="temp.txt",
            document_content=b"Hello",
            document_mimetype="text/plain",
        )
        self.officer_login(officers_factories.create_booking_secretary())
        response = self.get_literal_url(info.document.url)
        assert response.status_code == 200


@given(st.emails())
def test_decode_inverts_encode(email):
    v = EmailVerifyTokenGenerator()
    assert v.email_from_token(v.token_for_email(email)) == email


@given(st.emails())
def test_truncated_returns_invalid(email):
    v = EmailVerifyTokenGenerator()
    assert isinstance(v.email_from_token(v.token_for_email(email)[2:]), VerifyFailed)


@given(st.emails())
def test_expired_returns_expired(email):
    v = EmailVerifyTokenGenerator()
    assert v.email_from_token(v.token_for_email(email), max_age=-1) == VerifyExpired(email)


@given(email=st.text())
@example(email="abcdefgh")  # b64 encode results in trailing ==
def test_tolerate_truncated_trailing_equals(email):
    v = EmailVerifyTokenGenerator()

    # Either some silly people, or some dumb email programs, decide to strip
    # trailing = from URLs (despite this being a supposedly URL safe
    # character). Ensure that we tolerate this.

    def remove_equals(s):
        return s.rstrip("=")

        assert v.email_from_token(remove_equals(v.token_for_email(email))) == email
