from datetime import date, timedelta
from typing import Optional

import pytest
from time_machine import travel

from cciw.contact_us.models import Message
from cciw.data_retention import Group, ModelDetail, Policy, Rules, apply_data_retention, parse_keep
from cciw.officers.models import Application
from cciw.officers.tests.base import factories
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

        with travel("2017-01-01 00:00:00"):
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

        officer = factories.create_officer()
        start = date.today()
        application = factories.create_application(
            officer,
            date_saved=start,
            full_name=(full_name := "Charlie Cook"),
            birth_date=(dob := date(1960, 5, 6)),
            address_firstline=(address := "1 The Way")
        )
        with travel(start + timedelta(days=360)):
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

    # TODO Tests for contact_us.Message, mailer.Message, mailer.MessageLog
