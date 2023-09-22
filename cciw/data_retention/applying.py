# See config/data_retention.yaml
#
# Terminology:
#
# In data_retention.yaml, we use more "human friendly" terminology.
# We translate that to more precise, useful terminology that we want
# to use in code as part of load_data_retention_policy.

# We use 'erase' in this code to distinguish from 'delete'
#
# - delete refers specifically to a database delete,
#   in which the entire row is removed.
#
# - erasure is a more general concept that can refer
#   to a range of different erasing methods.
from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import cached_property
from typing import Protocol

from django.db import models, transaction
from django.db.models.expressions import RawSQL
from django.db.models.fields import Field
from django.db.models.query import QuerySet
from django.utils import timezone
from django_countries.fields import CountryField
from mailer import models as mailer_models
from paypal.standard.ipn.models import PayPalIPN

from cciw.accounts.models import User
from cciw.bookings.models import (
    KEEP_FINANCIAL_RECORDS_FOR,
    Booking,
    BookingAccount,
    SupportingInformation,
    SupportingInformationDocument,
)
from cciw.contact_us.models import Message
from cciw.officers.models import Application

from .datatypes import ErasureMethod, ForeverType, Group, ModelDetail


def load_actual_data_retention_policy():
    from .loading import load_data_retention_policy

    return load_data_retention_policy(available_erasure_methods=CUSTOM_ERASURE_METHODS)


def apply_data_retention(policy=None, ignore_missing_models=False):
    from .checking import get_data_retention_policy_issues

    if policy is None:
        policy = load_actual_data_retention_policy()

    issues = get_data_retention_policy_issues(policy)
    if issues:
        if ignore_missing_models:
            # Easier testing
            issues = [issue for issue in issues if "Missing models" not in issue.msg]
        if issues:
            raise AssertionError("Invalid data retention policy, aborting", issues)

    today = timezone.now()
    with transaction.atomic():
        for group in policy.groups:
            for model_detail in group.models:
                apply_data_retention_single_model(now=today, group=group, model_detail=model_detail)


def apply_data_retention_single_model(*, now: datetime, group: Group, model_detail: ModelDetail) -> None:
    rules = group.rules
    if isinstance(rules.keep, ForeverType):
        return
    erase_before_datetime = now - rules.keep
    records = get_automatically_erasable_records(now, erase_before_datetime, model_detail.model)
    build_single_model_erase_command(
        now=now,
        group=group,
        model_detail=model_detail,
        records=records,
    ).execute()


class EraseCommand(Protocol):
    def execute(self) -> None:
        ...

    # The following are used for manual erasure requests
    group: Group

    @property
    def is_empty(self) -> bool:
        ...

    @property
    def summary(self) -> str:
        ...

    @property
    def details(self) -> str:
        ...

    def as_json(self) -> dict:
        ...


RECORD_IN_USE_MESSAGE = "Record could not be erased. This is normally because it is in use for business purposes. "


class DeleteCommand:
    def __init__(self, *, group: Group, records: QuerySet):
        self.group: Group = group
        self.records = records

    def execute(self) -> None:
        self.records.delete()

    execute.alters_data = True

    @property
    def is_empty(self) -> bool:
        return self.record_count == 0

    @property
    def summary(self) -> str:
        return f"Delete {self.record_count} `{self.records.model._meta.label}` record(s)"

    @property
    def details(self) -> str:
        if self.record_count == 0:
            return RECORD_IN_USE_MESSAGE
        return "The whole record will be deleted."

    @cached_property
    def record_count(self) -> int:
        return self.records.count()

    def as_json(self):
        return {
            "type": "DeleteCommand",
            "group": {"name": self.group.name},
            "records": [
                {
                    "model": record._meta.label,
                    "pk": record.pk,
                }
                for record in self.records
            ],
        }


class UpdateCommand:
    def __init__(self, *, group: Group, records: QuerySet, update_dict: dict):
        self.group: Group = group
        self.records = records
        self.update_dict = update_dict

    def execute(self):
        self.records.update(**self.update_dict)

    @property
    def is_empty(self) -> bool:
        return self.record_count == 0

    @property
    def summary(self) -> str:
        return f"Erase columns from {self.record_count} `{self.records.model._meta.label}` record(s)"

    @property
    def details(self) -> str:
        if self.record_count == 0:
            return RECORD_IN_USE_MESSAGE
        return "The following columns will be erased:\n" + "\n".join(
            f" - {key}" for key in self.update_dict.keys() if key != "erased_on"
        )

    @cached_property
    def record_count(self) -> int:
        return self.records.count()

    def as_json(self):
        return {
            "type": "UpdateCommand",
            "group": {"name": self.group.name},
            "records": [
                {
                    "model": record._meta.label,
                    "pk": record.pk,
                }
                for record in self.records
            ],
            "update_dict": {
                "keys": list(self.update_dict.keys()),
            },
        }


def get_not_in_use_records(now: datetime, model: type):
    """
    For a model, returns records that are not in business use
    """
    # This is important as a top-level function only for data erasure requests.
    # For automatic data scrubbing, it is get_automatically_erasable_records() that counts
    return NOT_IN_USE_METHODS[model](now)


def get_automatically_erasable_records(now: datetime, before_datetime: date, model: type):
    not_in_use_qs = get_not_in_use_records(now, model)
    qs = OLDER_THAN_METHODS[model](not_in_use_qs, before_datetime)
    assert qs.model == model
    return qs


def build_single_model_erase_command(
    *,
    now: datetime,
    group: Group,
    model_detail: ModelDetail,
    records: QuerySet,
) -> EraseCommand:
    if model_detail.delete_row:
        return DeleteCommand(group=group, records=records)

    else:
        update_dict = {}
        for field in model_detail.fields:
            if field in model_detail.custom_erasure_methods:
                method = model_detail.custom_erasure_methods[field]
            else:
                method = find_erasure_method(field)
            update_dict.update(method.build_update_dict(field))
        if model_detail.model not in ERASED_ON_EXCEPTIONS:
            update_dict["erased_on"] = update_erased_on_field(now)
        return UpdateCommand(group=group, records=records, update_dict=update_dict)


def update_erased_on_field(now: datetime):
    return RawSQL(
        """
        CASE WHEN erased_on IS NULL THEN %s
        ELSE erased_on
        END
    """,
        [now],
    )


# --- Default erasure methods ---


DELETED_STRING = "[deleted]"
DELETED_BYTES = b"[deleted]"


# For EmailFieldErasure and CountryFieldErasure we avoid validation errors in
# admin by setting something that is valid, rather than just deleting.


class EmailFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.EmailField)

    def build_update_dict(self, field: Field):
        key = field.name
        if field.null and field.blank:
            return {key: None}
        else:
            return {key: "deleted@example.com"}


class CountryFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, CountryField)

    def build_update_dict(self, field: Field):
        key = field.name
        if field.null and field.blank:
            return {key: None}
        else:
            return {key: "GB"}  # United Kingdom


class CharFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.CharField)

    def build_update_dict(self, field: Field):
        key = field.name
        if field.null:
            return {key: None}
        elif field.max_length is not None and (field.max_length < len(DELETED_STRING)):
            return {key: ""}
        else:
            return {key: DELETED_STRING}


class TextFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.TextField)

    def build_update_dict(self, field: Field):
        key = field.name
        if field.null:
            return {key: None}
        else:
            return {key: DELETED_STRING}


class BinaryFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.BinaryField)

    def build_update_dict(self, field: Field):
        key = field.name
        if field.null:
            return {key: None}
        else:
            return {key: DELETED_BYTES}


class BooleanFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.BooleanField)

    def build_update_dict(self, field: Field):
        # Set to default value.
        return {field.name: field.default}


class IntegerFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return isinstance(field, models.IntegerField)

    def build_update_dict(self, field: Field):
        return {field.name: 0}


class NullableFieldErasure(ErasureMethod):
    def allowed_for_field(self, field: Field):
        return field.null

    def build_update_dict(self, field: Field):
        return {field.name: None}


# This list is ordered to prioritise more specific methods
DEFAULT_ERASURE_METHODS: list[ErasureMethod] = [
    EmailFieldErasure(),
    CountryFieldErasure(),
    CharFieldErasure(),
    TextFieldErasure(),
    BinaryFieldErasure(),
    BooleanFieldErasure(),
    IntegerFieldErasure(),
    NullableFieldErasure(),
]


def find_erasure_method(field):
    for method in DEFAULT_ERASURE_METHODS:
        if method.allowed_for_field(field):
            return method
    raise LookupError(f"No erasure method found for field {field.model.__name__}.{field.name}")


# --- Domain specific knowledge ---


# Dictionaries from model to callable for retrieving erasable records:

NOT_IN_USE_METHODS = {
    Message: lambda now: Message.objects.not_in_use(now),
    Application: lambda now: Application.objects.not_in_use(now),
    Booking: lambda now: Booking.objects.not_in_use(now),
    BookingAccount: lambda now: BookingAccount.objects.not_in_use(now),
    User: lambda now: User.objects.not_in_use(now),
    SupportingInformation: lambda now: SupportingInformation.objects.not_in_use(now),
    SupportingInformationDocument: lambda now: SupportingInformationDocument.objects.not_in_use(now),
    # 3rd party models: (that's why they don't have their own `not_in_use()` QuerySet method)
    #
    # If a message hasn't been sent for more than a month of being on the queue, assume
    # a permanent problem and that we can delete:
    mailer_models.Message: lambda now: mailer_models.Message.objects.filter(when_added__lt=now - timedelta(days=30)),
    # No MessageLogs are in use - they are a log of what has happened:
    mailer_models.MessageLog: lambda now: mailer_models.MessageLog.objects.all(),
    # PayPal records must be kept as financial records
    PayPalIPN: lambda now: PayPalIPN.objects.filter(created_at__lt=now - KEEP_FINANCIAL_RECORDS_FOR),
}

OLDER_THAN_METHODS = {
    Message: lambda qs, before_datetime: qs.older_than(before_datetime),
    Application: lambda qs, before_datetime: qs.older_than(before_datetime),
    Booking: lambda qs, before_datetime: qs.older_than(before_datetime),
    BookingAccount: lambda qs, before_datetime: qs.older_than(before_datetime),
    User: lambda qs, before_datetime: qs.older_than(before_datetime),
    SupportingInformation: lambda qs, before_datetime: qs.older_than(before_datetime),
    SupportingInformationDocument: lambda qs, before_datetime: qs.older_than(before_datetime),
    # 3rd party:
    mailer_models.Message: lambda qs, before_datetime: qs.filter(when_added__lt=before_datetime),
    mailer_models.MessageLog: lambda qs, before_datetime: qs.filter(when_added__lt=before_datetime),
    PayPalIPN: lambda qs, before_datetime: qs.filter(created_at__lt=before_datetime),
}


# Models for which we don't expect an 'erased_on' field:
ERASED_ON_EXCEPTIONS = [
    # This is in a 3rd party library, can't add a field to it:
    PayPalIPN,
]


class PreserveAgeOnCamp(ErasureMethod):
    def allowed_for_field(self, field):
        return field.model == Booking and field.name == "date_of_birth"

    def build_update_dict(self, field: Field):
        return {
            "date_of_birth":
            # Birthdates after YYYY-08-31 get counted as next school year,
            # so we anonymise those to YYYY-12-01, everything else to YYYY-01-01
            # See also Booking.age_base_date
            # See also BookingManager.need_approving
            RawSQL(
                """
            make_date(
                EXTRACT(YEAR FROM date_of_birth)::int,
                CASE WHEN EXTRACT(MONTH FROM date_of_birth) > 8 THEN 12
                     ELSE 1
                END,
                1
            )
            """,
                [],
                models.DateTimeField(),
            ),
        }


CUSTOM_ERASURE_METHODS = {
    "preserve age on camp": PreserveAgeOnCamp(),
}
