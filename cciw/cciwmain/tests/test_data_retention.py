from datetime import date, datetime, timedelta
from typing import Optional

import mailer as queued_mail
import pytest
from django.utils import timezone
from mailer import models as mailer_models
from time_machine import travel

from cciw.bookings import models as bookings_models
from cciw.bookings.tests import factories as bookings_factories
from cciw.cciwmain.tests.base import factories as camps_factories
from cciw.contact_us.models import Message
from cciw.data_retention import Group, ModelDetail, Policy, Rules, apply_data_retention, parse_keep
from cciw.mail.tests import send_queued_mail
from cciw.officers.models import Application
from cciw.officers.tests.base import factories as officers_factories
from cciw.utils.tests.base import TestBase


def test_parse_keep_forever():
    assert parse_keep('forever') is None


def test_parse_keep_years():
    assert parse_keep('3 years') == timedelta(days=3 * 365)


def test_parse_keep_other():
    with pytest.raises(ValueError):
        parse_keep('abc 123')


def make_policy(*, model: type, fields: list[str] = None, erase_after: Optional[timedelta] = None,
                delete_row=False):
    if fields is None:
        fields = []
    else:
        model_field_list = model._meta.get_fields()
        field_dict = {f.name: f for f in model_field_list}
        fields = [field_dict[f] for f in fields]
    model_detail = ModelDetail(
        model=model,
        fields=fields,
        delete_row=delete_row,
    )
    return Policy(source='test',
                  groups=[
                      Group(
                          rules=Rules(
                              erase_after=erase_after,
                              erasable_on_request=False
                          ),
                          models=[model_detail]
                      )
                  ])


def apply_partial_policy(policy):
    return apply_data_retention(policy, ignore_missing_models=True)


class TestApplyDataRetentionPolicy(TestBase):
    def test_delete_row(self):
        policy = make_policy(
            model=Message,
            delete_row=True,
            erase_after=timedelta(days=365),
        )

        with travel("2017-01-01 00:05:00"):
            Message.objects.create(email='bob@example.com', name='Bob', message='Hello')
            apply_partial_policy(policy)
            assert Message.objects.count() == 1

        with travel("2017-12-31 23:00:00"):
            apply_partial_policy(policy)
            assert Message.objects.count() == 1
            Message.objects.create(email='bob@example.com', name='Bob', message='Hello 2')
            apply_partial_policy(policy)
            assert Message.objects.count() == 2  # neither is deleted

        with travel("2018-01-01 01:00:00"):
            apply_partial_policy(policy)
            assert Message.objects.count() == 1
            message = Message.objects.get()
            assert message.message == 'Hello 2'

        with travel("2019-01-01 01:00:00"):
            apply_partial_policy(policy)
            assert Message.objects.count() == 0

    def test_blank_data(self):
        policy = make_policy(
            model=Application,
            fields=[
                'address_firstline',  # string
                'birth_date',  # nullable date
            ],
            erase_after=timedelta(days=365),
        )

        officer = officers_factories.create_officer()
        start = date.today()
        application = officers_factories.create_application(
            officer,
            date_saved=start,
            full_name=(full_name := "Charlie Cook"),
            birth_date=(dob := date(1960, 5, 6)),
            address_firstline=(address := "1 The Way")
        )
        with travel(start + timedelta(days=365)):
            apply_partial_policy(policy)
            application.refresh_from_db()
            assert application.birth_date == dob
            assert application.address_firstline == address

        with travel(start + timedelta(days=366)):
            apply_partial_policy(policy)
            application.refresh_from_db()
            assert application.birth_date is None
            assert application.address_firstline == "[deleted]"
            assert application.full_name == full_name

    def test_erase_contact_us_Message(self):
        policy = make_policy(
            model=Message,
            delete_row=True,
            erase_after=timedelta(days=365),
        )
        start = timezone.now()
        message = officers_factories.create_contact_us_message()
        self._assert_instance_deleted_after(instance=message, start=start, policy=policy, days=365)

    def test_erase_mailer_Message(self):
        policy = make_policy(
            model=mailer_models.Message,
            delete_row=True,
            erase_after=timedelta(days=365),
        )

        queued_mail.send_mail('Subject', 'message', 'from@example.com', ['to@example.com'])
        start = timezone.now()
        message = mailer_models.Message.objects.get()
        self._assert_instance_deleted_after(instance=message, start=start, policy=policy, days=365)

    def test_erase_mailer_MessageLog(self):
        policy = make_policy(
            model=mailer_models.MessageLog,
            delete_row=True,
            erase_after=timedelta(days=365),
        )

        queued_mail.send_mail('Subject', 'message', 'from@example.com', ['to@example.com'])
        send_queued_mail()
        start = timezone.now()
        message_log = mailer_models.MessageLog.objects.get()
        self._assert_instance_deleted_after(instance=message_log, start=start, policy=policy, days=365)

    def test_erase_Booking(self):
        policy = make_policy(
            model=bookings_models.Booking,
            delete_row=False,
            erase_after=timedelta(days=365),
            fields=[
                'address_line1',
            ],
        )
        with travel('2001-01-01'):
            booking = bookings_factories.create_booking(address_line1='123 Main St')

        with travel('2001-12-31'):
            apply_partial_policy(policy)
            booking.refresh_from_db()
            assert booking.address_line1 == '123 Main St'

        with travel('2002-01-01 01:00:00'):
            apply_partial_policy(policy)
            booking.refresh_from_db()
            assert booking.address_line1 == '[deleted]'

    # TODO PreserveAgeOnCamp test and implement

    def test_erase_BookingAccount(self):
        policy = make_policy(
            model=bookings_models.BookingAccount,
            delete_row=False,
            erase_after=timedelta(days=365),
            fields=[
                'address_line1',
            ],
        )
        with travel('2001-01-01'):
            account = bookings_factories.create_booking_account(
                address_line1='123 Main St',
            )
        with travel('2001-12-31'):
            apply_partial_policy(policy)
            account.refresh_from_db()
            assert account.address_line1 == '123 Main St'
        with travel('2002-01-01 01:00:00'):
            apply_partial_policy(policy)
            account.refresh_from_db()
            assert account.address_line1 == '[deleted]'

    def test_erase_BookingAccount_last_login(self):
        policy = make_policy(
            model=bookings_models.BookingAccount,
            delete_row=False,
            erase_after=timedelta(days=365),
            fields=[
                'address_line1',
            ],
        )
        with travel('2001-01-01'):
            account = bookings_factories.create_booking_account(
                address_line1='123 Main St',
            )
        with travel('2001-10-01'):
            account.last_login = timezone.now()
            account.save()
            assert account.address_line1 == '123 Main St'
        with travel('2002-01-01 01:00:00'):
            apply_partial_policy(policy)
            account.refresh_from_db()
            assert account.address_line1 == '123 Main St'
        with travel('2002-10-02 01:00:00'):
            apply_partial_policy(policy)
            account.refresh_from_db()
            assert account.address_line1 == '[deleted]'

    def test_erase_BookingAccount_not_in_use_payment_outstanding(self):
        policy = make_policy(
            model=bookings_models.BookingAccount,
            delete_row=False,
            erase_after=timedelta(days=365),
            fields=[
                'address_line1',
            ],
        )
        with travel('2001-01-01'):
            account = bookings_factories.create_booking_account(
                address_line1='123 Main St',
            )
            bookings_factories.create_booking(
                account=account,
                state=bookings_models.BookingState.BOOKED,
                amount_due=100,
            )
        with travel('2011-01-01'):
            # Should not be deleted despite age, because we have outstanding
            # payments due.
            apply_partial_policy(policy)
            account.refresh_from_db()
            assert account.address_line1 == '123 Main St'

    def test_erase_BookingAccount_not_in_use_current_booking(self):
        account = bookings_factories.create_booking_account()
        assert account in bookings_models.BookingAccount.objects.not_in_use()
        camp = camps_factories.create_camp(start_date=date.today())
        bookings_factories.create_booking(
            account=account,
            state=bookings_models.BookingState.BOOKED,
            camp=camp,
            amount_due=0,
        )
        assert account not in bookings_models.BookingAccount.objects.not_in_use()

        with travel(camp.end_date + timedelta(days=1)):
            assert account in bookings_models.BookingAccount.objects.not_in_use()

            # Now have past booking, one future booking - should be 'in use' again
            camp2 = camps_factories.create_camp(start_date=date.today())
            bookings_factories.create_booking(
                account=account,
                state=bookings_models.BookingState.BOOKED,
                camp=camp2,
                amount_due=0,
            )

            assert account not in bookings_models.BookingAccount.objects.not_in_use()

        with travel(camp2.end_date + timedelta(days=1)):
            assert account in bookings_models.BookingAccount.objects.not_in_use()

    def _assert_instance_deleted_after(self, *, instance: object, start: datetime, policy: Policy, days: int):
        model = instance.__class__
        with travel(start + timedelta(days=days) - timedelta(seconds=10)):
            apply_partial_policy(policy)
            assert model.objects.filter(id=instance.id).count() == 1

        with travel(start + timedelta(days=days) + timedelta(seconds=10)):
            apply_partial_policy(policy)
            assert model.objects.filter(id=instance.id).count() == 0
