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

from datetime import date, datetime

from django.db import models, transaction
from django.db.models.expressions import RawSQL
from django.db.models.fields import Field
from django.utils import timezone
from django_countries.fields import CountryField
from mailer import models as mailer_models
from paypal.standard.ipn.models import PayPalIPN

from cciw.accounts.models import User
from cciw.bookings.models import Booking, BookingAccount, SupportingInformation, SupportingInformationDocument
from cciw.contact_us.models import Message
from cciw.officers.models import Application

from .datatypes import ErasureMethod, ForeverType, ModelDetail, Rules


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
    retval = []
    with transaction.atomic():
        for group in policy.groups:
            for model_detail in group.models:
                retval.append(apply_data_retention_single_model(today, rules=group.rules, model_detail=model_detail))
    return retval


def apply_data_retention_single_model(now: datetime, *, rules: Rules, model_detail: ModelDetail):
    if isinstance(rules.keep, ForeverType):
        return []

    erase_before_datetime = now - rules.keep
    # TODO probably want separate method for manual erasure requests,
    # need to be careful about things that are still needed and
    # how to respect `keep`
    erasable_records = get_erasable(erase_before_datetime, model_detail.model)
    if model_detail.delete_row:
        retval = erasable_records.delete()
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
        retval = erasable_records.update(**update_dict)
    return retval


def get_erasable(before_datetime: date, model: type):
    qs = ERASABLE_RECORDS[model](before_datetime)
    assert qs.model == model
    return qs


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
        elif field.max_length < len(DELETED_STRING):
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


# Dictionary from model to callable that retrieves the erasable records:
ERASABLE_RECORDS = {
    Message: lambda before_datetime: Message.objects.older_than(before_datetime),
    Application: lambda before_datetime: Application.objects.older_than(before_datetime),
    Booking: lambda before_datetime: Booking.objects.not_in_use().older_than(before_datetime),
    BookingAccount: lambda before_datetime: BookingAccount.objects.not_in_use().older_than(before_datetime),
    User: lambda before_datetime: User.objects.older_than(before_datetime),
    SupportingInformation: lambda before_datetime: SupportingInformation.objects.older_than(before_datetime),
    SupportingInformationDocument: lambda before_datetime: SupportingInformationDocument.objects.older_than(
        before_datetime
    ),
    # 3rd party:
    mailer_models.Message: lambda before_datetime: mailer_models.Message.objects.filter(
        when_added__lt=before_datetime,
    ),
    mailer_models.MessageLog: lambda before_datetime: mailer_models.MessageLog.objects.filter(
        when_added__lt=before_datetime,
    ),
    PayPalIPN: lambda before_datetime: PayPalIPN.objects.filter(
        created_at__lt=before_datetime,
    ),
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
