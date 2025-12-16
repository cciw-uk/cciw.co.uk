from datetime import date, datetime, timedelta

import mailer as queued_mail
import pytest
from django.db.models.base import Model
from django.utils import timezone
from mailer import models as mailer_models
from paypal.standard.ipn.models import PayPalIPN
from time_machine import travel

from cciw.accounts.models import User
from cciw.bookings.models import Booking, BookingAccount, BookingState
from cciw.bookings.tests import factories as bookings_factories
from cciw.cciwmain.tests import factories as camps_factories
from cciw.cciwmain.tests.utils import date_to_datetime, make_datetime
from cciw.contact_us import tests as contact_us_factories
from cciw.contact_us.models import Message
from cciw.data_retention.applying import NOT_IN_USE_METHODS, PreserveAgeOnCamp, apply_data_retention
from cciw.data_retention.datatypes import ErasureMethod, Forever, Group, Keep, ModelDetail, Policy, Rules
from cciw.data_retention.loading import parse_keep
from cciw.mail.tests import send_queued_mail
from cciw.officers.models import Application
from cciw.officers.tests import factories as officers_factories


def test_parse_keep_forever():
    assert parse_keep("forever") is Forever


def test_parse_keep_years():
    assert parse_keep("3 years") == timedelta(days=3 * 365)


def test_parse_keep_days():
    assert parse_keep("4 days") == timedelta(days=4)


def test_parse_keep_other():
    with pytest.raises(ValueError):
        parse_keep("abc 123")


def make_policy(
    *,
    model: type[Model],
    fields: list[str] = None,
    keep: Keep,
    delete_row=False,
    custom_erasure_methods: dict[str, ErasureMethod] = None,
):
    model_field_list = model._meta.get_fields()
    field_dict = {f.name: f for f in model_field_list}
    if fields is None:
        fields = []
    else:
        fields = [field_dict[f] for f in fields]
    if custom_erasure_methods is None:
        custom_erasure_methods = {}
    else:
        custom_erasure_methods = {field_dict[name]: method for name, method in custom_erasure_methods.items()}
    model_detail = ModelDetail(
        model=model,
        fields=fields,
        delete_row=delete_row,
        custom_erasure_methods=custom_erasure_methods,
    )
    return Policy(
        source="test",
        groups=[Group(name="A name", rules=Rules(keep=keep, erasable_on_request=False), models=[model_detail])],
    )


def apply_partial_policy(policy):
    return apply_data_retention(policy, ignore_missing_models=True)


def test_delete_row(db):
    policy = make_policy(
        model=Message,
        delete_row=True,
        keep=timedelta(days=365),
    )

    with travel("2017-01-01 00:05:00"):
        contact_us_factories.create_message(message="Hello")
        apply_partial_policy(policy)
        assert Message.objects.count() == 1

    with travel("2017-12-31 23:00:00"):
        apply_partial_policy(policy)
        assert Message.objects.count() == 1
        contact_us_factories.create_message(message="Hello 2")
        apply_partial_policy(policy)
        assert Message.objects.count() == 2  # neither is deleted

    with travel("2018-01-01 01:00:00"):
        apply_partial_policy(policy)
        assert Message.objects.count() == 1
        message = Message.objects.get()
        assert message.message == "Hello 2"

    with travel("2019-01-01 01:00:00"):
        apply_partial_policy(policy)
        assert Message.objects.count() == 0


def test_blank_data(db):
    policy = make_policy(
        model=Application,
        fields=[
            "address_firstline",  # string
            "birth_date",  # nullable date
        ],
        keep=timedelta(days=365),
    )

    officer = officers_factories.create_officer()
    start = date.today()
    application = officers_factories.create_application(
        officer,
        saved_on=start,
        full_name=(full_name := "Charlie Cook"),
        birth_date=(dob := date(1960, 5, 6)),
        address_firstline=(address := "1 The Way"),
    )
    with travel(start + timedelta(days=365)):
        apply_partial_policy(policy)
        application.refresh_from_db()
        assert application.birth_date == dob
        assert application.address_firstline == address

    with travel(start + timedelta(days=366)):
        erased_date = date.today()
        apply_partial_policy(policy)
        application.refresh_from_db()
        assert application.birth_date is None
        assert application.address_firstline == "[deleted]"
        assert application.full_name == full_name
        assert application.erased_at.date() == erased_date

    with travel(start + timedelta(days=466)):
        apply_partial_policy(policy)
        application.refresh_from_db()
        assert application.erased_at.date() == erased_date


def test_erase_contact_us_Message(db):
    policy = make_policy(
        model=Message,
        delete_row=True,
        keep=timedelta(days=365),
    )
    start = timezone.now()
    message = contact_us_factories.create_message()
    _assert_instance_deleted_after(instance=message, start=start, policy=policy, days=365)


def test_erase_mailer_Message(db):
    policy = make_policy(
        model=mailer_models.Message,
        delete_row=True,
        keep=timedelta(days=365),
    )

    # We use django-mailer here explicitly, rather than django.core.mail,
    # because we need to test the cleanup of Message objects, and in tests
    # Django swaps out the email backend to a dummy one that doesn't use
    # django_mailer at all.
    queued_mail.send_mail("[CCIW] Subject", "message", "from@example.com", ["to@example.com"])
    start = timezone.now()
    message = mailer_models.Message.objects.get()
    _assert_instance_deleted_after(instance=message, start=start, policy=policy, days=365)


def test_erase_mailer_MessageLog(db):
    policy = make_policy(
        model=mailer_models.MessageLog,
        delete_row=True,
        keep=timedelta(days=365),
    )

    queued_mail.send_mail("[CCIW] Subject", "message", "from@example.com", ["to@example.com"])
    send_queued_mail()
    start = timezone.now()
    message_log = mailer_models.MessageLog.objects.get()
    _assert_instance_deleted_after(instance=message_log, start=start, policy=policy, days=365)


def test_erase_Booking(db):
    policy = make_policy(
        model=Booking,
        delete_row=False,
        keep=timedelta(days=365),
        fields=[
            "address_line1",
        ],
    )
    with travel("2001-01-01"):
        booking = bookings_factories.create_booking(address_line1="123 Main St")

    end_of_camp = date_to_datetime(booking.camp.end_date) + timedelta(days=1)
    with travel(end_of_camp + timedelta(days=365) - timedelta(seconds=10)):
        apply_partial_policy(policy)
        booking.refresh_from_db()
        assert booking.address_line1 == "123 Main St"

    with travel(end_of_camp + timedelta(days=365) + timedelta(seconds=10)):
        apply_partial_policy(policy)
        booking.refresh_from_db()
        assert booking.address_line1 == "[deleted]"


def test_erase_Booking_PreserveAgeOnCamp(db):
    policy = make_policy(
        model=Booking,
        delete_row=False,
        keep=timedelta(days=365),
        fields=["birth_date"],
        custom_erasure_methods={"birth_date": PreserveAgeOnCamp()},
    )
    for birth_date, age_on_camp in [
        (date(1988, 8, 31), 13),
        (date(1988, 9, 1), 12),
    ]:
        with travel("2001-01-01"):
            camp = camps_factories.create_camp(start_date=date(2001, 8, 1))
            booking = bookings_factories.create_booking(
                camp=camp,
                birth_date=birth_date,
            )
            assert booking.birth_date == birth_date
            assert booking.age_on_camp() == age_on_camp

        with travel(booking.camp.end_date + timedelta(days=365 + 1)):
            apply_partial_policy(policy)
            booking.refresh_from_db()
            assert booking.age_on_camp() == age_on_camp
            assert booking.birth_date.year == birth_date.year
            assert booking.birth_date != birth_date


def test_erase_BookingAccount(db):
    """
    Test erasing BookingAccount works
    """
    # Implicitly checks the `not_in_use()` method,
    # and the `created_at` check in `older_than()` method.
    policy = make_policy(
        model=BookingAccount,
        delete_row=False,
        keep=timedelta(days=365),
        fields=[
            "address_line1",
        ],
    )
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account(
            address_line1="123 Main St",
        )
    with travel("2001-12-31"):
        apply_partial_policy(policy)
        account.refresh_from_db()
        assert account.address_line1 == "123 Main St"
    with travel("2002-01-01 01:00:00"):
        apply_partial_policy(policy)
        account.refresh_from_db()
        assert account.address_line1 == "[deleted]"


def test_BookingAccount_older_than_respects_last_login_at(db):
    # Use of `travel()` is not necessary here because `older_than()` takes
    # explicit datetime object, but it helps keep all the tests consistent
    # in style.
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account(
            address_line1="123 Main St",
        )
    with travel("2001-10-01"):
        account.last_login_at = timezone.now()
        account.save()
    with travel("2002-01-01 01:00:00"):
        assert account not in BookingAccount.objects.not_in_use(timezone.now()).older_than(
            timezone.now() - timedelta(days=365)
        )
    with travel("2002-10-02 01:00:00"):
        assert account in BookingAccount.objects.not_in_use(timezone.now()).older_than(
            timezone.now() - timedelta(days=365)
        )


def test_BookingAccount_not_in_use_respects_payment_outstanding(db):
    policy = make_policy(
        model=BookingAccount,
        delete_row=False,
        keep=timedelta(days=365),
        fields=[
            "address_line1",
        ],
    )
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account(
            address_line1="123 Main St",
        )
        bookings_factories.create_booking(
            account=account,
            state=BookingState.BOOKED,
            amount_due=100,
        )
    with travel("2011-01-01"):
        assert account not in BookingAccount.objects.not_in_use(timezone.now())
        # Should not be deleted despite age, because we have outstanding
        # payments due.
        apply_partial_policy(policy)
        account.refresh_from_db()
        assert account.address_line1 == "123 Main St"


def test_BookingAccount_not_in_use_respects_current_booking(db):
    account = bookings_factories.create_booking_account()
    assert account in BookingAccount.objects.not_in_use(timezone.now())
    camp = camps_factories.create_camp(start_date=date.today())
    bookings_factories.create_booking(
        account=account,
        state=BookingState.BOOKED,
        camp=camp,
        amount_due=0,
    )
    assert account not in BookingAccount.objects.not_in_use(timezone.now())

    with travel(camp.end_date + timedelta(days=1)):
        assert account in BookingAccount.objects.not_in_use(timezone.now())

        # Now have past booking, one future booking - should be 'in use' again
        camp2 = camps_factories.create_camp(start_date=date.today())
        bookings_factories.create_booking(
            account=account,
            state=BookingState.BOOKED,
            camp=camp2,
            amount_due=0,
        )

        assert account not in BookingAccount.objects.not_in_use(timezone.now())

    with travel(camp2.end_date + timedelta(days=1)):
        assert account in BookingAccount.objects.not_in_use(timezone.now())


def test_BookingAccount_not_in_use_query_issue(db):
    # Had some issues with not_in_use() and older_than() combinations with
    # more implementations of them. The error
    # "django.db.utils.ProgrammingError: more than one row returned by a
    # subquery used as an expression." was produced. Looking at the query
    # created, which was rather suspect, it was possibly a Django bug. The
    # following code produced the issue, which was worked around by
    # structuring the query differently.
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account()
        other_account = bookings_factories.create_booking_account()
        camp1 = camps_factories.create_camp(start_date=date.today())
        camp2 = camps_factories.create_camp(start_date=date.today() + timedelta(days=14))
        for acc in (account, other_account):
            for camp in (camp1, camp2):
                bookings_factories.create_booking(
                    account=acc,
                    state=BookingState.BOOKED,
                    camp=camp,
                    amount_due=100,
                )
        account.receive_payment(2 * 100)
        other_account.receive_payment(100)

    with travel("2001-01-09"):
        # This has unfinished camps:
        assert account not in BookingAccount.objects.not_in_use(timezone.now()).older_than(make_datetime(2001, 1, 9))
    with travel("2002-01-01"):
        # Now has no outstanding fees, nor unfinished camps
        assert account in BookingAccount.objects.not_in_use(timezone.now()).older_than(make_datetime(2002, 1, 1))
        # This one has outstanding fees
        assert other_account not in BookingAccount.objects.not_in_use(timezone.now()).older_than(
            make_datetime(2002, 1, 1)
        )


def test_BookingAccount_older_than_respects_last_payment_date(db):
    """
    BookingAccount 'older than' should consider payment as similar
    to a login in terms of regarding the account as recent.
    """
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account()

    with travel("2001-02-01 01:00:00"):
        bookings_factories.create_processed_payment(account=account, amount=100)
        assert account not in BookingAccount.objects.not_in_use(timezone.now())  # due to non zero balance
        bookings_factories.create_processed_payment(account=account, amount=-100)
        assert account in BookingAccount.objects.not_in_use(timezone.now())  # due to zero balance

        # Although it is 'not_in_use', it is not yet considered as 'older_than(2001-02-01)'
        # because of payment
        assert account not in BookingAccount.objects.not_in_use(timezone.now()).older_than(make_datetime(2001, 2, 1))

        # It is older than 2001-02-02
        assert account in BookingAccount.objects.not_in_use(timezone.now()).older_than(make_datetime(2001, 2, 2))


def test_BookingAccount_older_than_respects_last_booking_camp_date(db):
    """
    BookingAccount 'older than' should consider a booking as similar
    to a login in terms of regarding the account as recent.
    """
    with travel("2001-01-01"):
        account = bookings_factories.create_booking_account()
        booking = bookings_factories.create_booking(account=account, state=BookingState.BOOKED, amount_due=0)

    after_camp = booking.camp.end_date + timedelta(days=10)
    with travel(after_camp):
        assert account in BookingAccount.objects.not_in_use(timezone.now())  # due to zero balance, and being after camp

        # But it is not older than end date of camp
        assert account not in BookingAccount.objects.not_in_use(timezone.now()).older_than(
            date_to_datetime(booking.camp.end_date)
        )
        assert account in BookingAccount.objects.not_in_use(timezone.now()).older_than(
            date_to_datetime(booking.camp.end_date) + timedelta(days=1)
        )


def test_erase_User(db):
    policy = make_policy(
        model=User,
        delete_row=False,
        keep=timedelta(days=365),
        fields=[
            "contact_phone_number",
        ],
    )
    with travel("2001-01-01"):
        user = officers_factories.create_officer(contact_phone_number=(num := "01234 567 890"))
    with travel("2001-12-31"):
        apply_partial_policy(policy)
        user.refresh_from_db()
        assert user.contact_phone_number == num
    with travel("2002-01-01 01:00:00"):
        apply_partial_policy(policy)
        user.refresh_from_db()
        assert user.contact_phone_number == "[deleted]"


def test_erase_PayPalIPN(db):
    policy = make_policy(
        model=PayPalIPN,
        delete_row=False,
        keep=timedelta(days=365),  # Less than KEEP_FINANCIAL_RECORDS_FOR
        fields=[
            "payer_business_name",
        ],
    )
    with travel("2001-01-01"):
        ipn = bookings_factories.create_ipn(payer_business_name=(name := "Peter"))
    with travel("2001-12-31"):
        apply_partial_policy(policy)
        ipn.refresh_from_db()
        assert ipn.payer_business_name == name
    with travel("2002-01-02 01:00:00"):
        # because the record is still in use, we don't delete

        # Lower level check
        assert not NOT_IN_USE_METHODS[PayPalIPN](timezone.now()).filter(id=ipn.id).exists()

        apply_partial_policy(policy)
        ipn.refresh_from_db()
        assert ipn.payer_business_name == "Peter"

    with travel("2004-01-02 01:00:00"):
        # Now we've reached KEEP_FINANCIAL_RECORDS_FOR limit
        apply_partial_policy(policy)
        ipn.refresh_from_db()
        assert ipn.payer_business_name == "[deleted]"


def test_keep_forever(django_assert_num_queries, db):
    policy = make_policy(
        model=Booking,
        delete_row=False,
        keep=Forever,
        fields=[
            "first_name",
        ],
    )
    with travel("2001-01-01"):
        booking = bookings_factories.create_booking(first_name="Mary")
    with travel("2101-01-01"):
        with django_assert_num_queries(2) as captured:
            apply_partial_policy(policy)

        booking.refresh_from_db()
        assert booking.first_name == "Mary"

        # No actual queries done, just the @atomic decorator:
        assert [q["sql"].split()[0] for q in captured.captured_queries] == ["SAVEPOINT", "RELEASE"]


def _assert_instance_deleted_after(*, instance: Model, start: datetime, policy: Policy, days: int):
    model = instance.__class__
    with travel(start + timedelta(days=days) - timedelta(seconds=10)):
        apply_partial_policy(policy)
        assert model.objects.filter(id=instance.id).count() == 1

    with travel(start + timedelta(days=days) + timedelta(seconds=10)):
        apply_partial_policy(policy)
        assert model.objects.filter(id=instance.id).count() == 0


# TODO
# tests for
#  Application.objects.not_in_use()
#  User.objects.not_in_use()
#  SupportingInformation.objects.not_in_use
#  SupportingInformationDocument.objects.not_in_use
