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

import dataclasses
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Union

import parsy
import pydantic.dataclasses
import yaml
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.checks import Error
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


class DataclassConfig:
    arbitrary_types_allowed = True


dataclass = pydantic.dataclasses.dataclass(config=DataclassConfig)

if TYPE_CHECKING:
    # Help some type checkers/IDE tools to understand pydantic
    from dataclasses import dataclass


# --- Policy and sub-components ---
#
# The YAML file is parsed into these objects.


@dataclass
class Policy:
    """
    The entire data retention policy, which we have only one of in production.
    """

    source: str
    groups: list[Group]


@dataclass
class Group:
    name: str
    rules: Rules
    models: list[ModelDetail]


@dataclass
class Rules:
    keep: Keep
    erasable_on_request: bool


@dataclass
class ModelDetail:
    model: type  # Model subclass
    fields: list[Field]
    custom_erasure_methods: dict[Field, ErasureMethod] = dataclasses.field(default_factory=dict)
    delete_row: bool = False

    @classmethod
    def build(
        cls,
        *,
        name: str,
        field_names: list[str] | None = None,
        all_fields: bool = False,
        erasure_method_names: dict[str, str] | None = None,
        delete_row: bool = False,
    ):
        model = apps.get_model(name)
        field_list = model._meta.get_fields()
        field_dict = {f.name: f for f in field_list}
        if delete_row:
            if field_names is not None:
                raise ValueError("If 'delete_row' is used, no columns should be specified.")
            if all_fields:
                raise ValueError("No need to specify all column if 'delete_row' is used.")
            if erasure_method_names:
                raise ValueError("If 'delete_row' is used, no erasure methods should be specified.")
            # We satisfy exhaustiveness checks easier with this:
            fields = [f for f in field_list if _field_requires_privacy_policy(f)]

        if erasure_method_names is None:
            erasure_method_names = {}
        if all_fields:
            assert field_names is None
            fields = [f for f in field_list if _field_requires_privacy_policy(f)]
        elif not delete_row:
            assert field_names is not None
            fields = []
            for f in field_names:
                if f not in field_dict:
                    raise ValueError(f"Model {model.__name__} does not have field {f}")
                fields.append(field_dict[f])

        erasure_methods = {}
        for field_name, method_name in erasure_method_names.items():
            field = field_dict[field_name]
            try:
                erasure_method = CUSTOM_ERASURE_METHODS[method_name]
            except KeyError:
                raise ValueError(f'Erasure method "{method_name}" not found')
            if not erasure_method.allowed_for_field(field):
                raise ValueError(f'Erasure method "{method_name}" not allowed for {model.__name__}.{field_name}')
            erasure_methods[field] = erasure_method
        return cls(
            model=model,
            fields=fields,
            custom_erasure_methods=erasure_methods,
            delete_row=delete_row,
        )


class ErasureMethod:
    def allowed_for_field(self, field: Field) -> bool:
        raise NotImplementedError(f"{self.__class__} needs to implement allowed_for_field")

    def build_update_dict(self, field) -> dict:
        """
        Returns a dict which can be passed as keyword arguments
        to a QuerySet.update() call.
        """
        raise NotImplementedError(f"{self.__class__} needs to implement build_update_dict")


class _Forever:
    pass


Forever = _Forever()

Keep = Union[timedelta, _Forever]


Policy.__pydantic_model__.update_forward_refs()
Group.__pydantic_model__.update_forward_refs()
Rules.__pydantic_model__.update_forward_refs()
ModelDetail.__pydantic_model__.update_forward_refs()

# --- Parsing and checking ---


def get_data_retention_policy_issues(policy: Policy | None = None):
    if policy is None:
        policy = load_data_retention_policy()
    return _check_exhaustiveness(policy) + _check_erasable_records(policy)


def load_data_retention_policy() -> Policy:
    """
    Loads data_retention.yaml
    """
    # This method parses (and validates) data_retention.yaml, and also converts
    # from more "human readable" names like "tables", "columns" etc. into the
    # kind of things we actually want to use from code ("model", "fields").

    # A lot of complexity here is trying to keep the YAML human readable and not
    # redundant, and making sure we validate against lots of possible errors.

    # File format/validity errors are allowed to propogate.
    # Other errors are handled more gracefully by get_data_retention_policy_issues.
    # Either way, we don't pass "manage.py check" if there are any problems.
    filename = settings.DATA_RETENTION_CONFIG_FILE
    policy_yaml = yaml.load(open(filename), Loader=yaml.SafeLoader)
    groups = []
    for yaml_group in policy_yaml:
        yaml_rules = yaml_group.pop("rules")
        keep = parse_keep(yaml_rules.pop("keep"))
        erasable_on_request = yaml_rules.pop("deletable on request from data subject")
        if yaml_rules:
            raise ValueError(f'Unexpected keys in "rules" entry: {", ".join(yaml_rules.keys())}')

        yaml_tables = yaml_group.pop("tables")
        models = []
        for yaml_table in yaml_tables:
            yaml_model_name = yaml_table.pop("name")
            yaml_columns = yaml_table.pop("columns", None)
            yaml_deletion_methods = yaml_table.pop("deletion methods", {})
            if yaml_columns == "all":
                if "delete row" in yaml_table:
                    raise ValueError('You should specify either "columns: all" or "delete row", not both')
                model_detail = ModelDetail.build(
                    name=yaml_model_name, all_fields=True, erasure_method_names=yaml_deletion_methods
                )
            else:
                yaml_delete_row = yaml_table.pop("delete row", False)
                if yaml_delete_row:
                    if yaml_columns is not None:
                        raise ValueError('You should specify either "columns" or "delete row: yes", not both')
                model_detail = ModelDetail.build(
                    name=yaml_model_name,
                    field_names=yaml_columns,
                    erasure_method_names=yaml_deletion_methods,
                    delete_row=yaml_delete_row,
                )
            models.append(model_detail)
            if yaml_table:
                raise ValueError(f'Unexpected keys in "tables" entry: {", ".join(yaml_table.keys())}')

        try:
            group_name = yaml_group.pop("group")
        except KeyError:
            raise ValueError('Every group should have a named defined in "group" key')
        groups.append(
            Group(
                name=group_name,
                rules=Rules(
                    keep=keep,
                    erasable_on_request=erasable_on_request,
                ),
                models=models,
            )
        )
        if yaml_group:
            raise ValueError(f'Unexpected keys in group entry: {", ".join(yaml_group.keys())}')

    return Policy(source=str(filename), groups=groups)


def _check_exhaustiveness(policy: Policy) -> list[Error]:
    all_models = apps.get_models()
    defined_fields = set()
    dupes = []
    for group in policy.groups:
        for model_detail in group.models:
            for field in model_detail.fields:
                key = (model_detail.model, field.name)
                if key in defined_fields:
                    dupes.append(key)
                defined_fields.add(key)
    missing = []
    for model in all_models:
        missing_for_model = []
        for field in model._meta.get_fields():
            if not _field_requires_privacy_policy(field):
                continue

            key = (model, field.name)
            if key not in defined_fields:
                missing_for_model.append(field)
        if missing_for_model:
            missing.append((model, missing_for_model))

    issues = []
    if dupes:
        issues.append(
            Error(
                "Duplicate policies were found for some fields:\n"
                + "".join(f"   - {model.__name__}.{field}\n" for model, field in dupes),
                obj=policy.source,
                id="dataretention.E001",
            )
        )
    if missing:
        msg_parts = ["Missing models/fields:"]
        for model, missing_for_model in missing:
            # Mimic the format of data_retention.yaml for easy copy/paste
            msg_parts.append(f"    - name: {model._meta.app_label}.{model.__name__}")
            msg_parts.append("      columns:")
            for field in missing_for_model:
                msg_parts.append(f"      - {field.name}")
        issues.append(
            Error(
                "\n".join(msg_parts) + "\n",
                obj=policy.source,
                id="dataretention.E002",
            )
        )

    return issues


def _check_erasable_records(policy: Policy) -> list[Error]:
    seen_models = set()
    issues = []
    for group in policy.groups:
        if group.rules.keep is Forever and not group.rules.erasable_on_request:
            # Don't need erasure method
            continue

        for model_detail in group.models:
            model = model_detail.model
            if model in seen_models:
                continue
            seen_models.add(model)
            if model not in ERASABLE_RECORDS:
                issues.append(
                    Error(
                        f"No method defined to obtain erasable records for {model.__name__}",
                        obj=policy.source,
                        id="dataretention.E003",
                    )
                )
            if not model_detail.delete_row:
                for field in model_detail.fields:
                    if field in model_detail.custom_erasure_methods:
                        continue
                    try:
                        _find_erasure_method(field)
                    except LookupError:
                        issues.append(
                            Error(
                                f"No method defined to erase field {field.model.__name__}.{field.name}",
                                obj=policy.source,
                                id="dataretention.E004",
                            )
                        )
                if "erased_on" not in [f.name for f in model._meta.get_fields()] and model not in ERASED_ON_EXCEPTIONS:
                    issues.append(
                        Error(
                            'No "erased_on" field present',
                            obj=model,
                            id="dataretention.E005",
                        )
                    )
    return issues


def _field_requires_privacy_policy(field: Field):
    # By default we don't need a policy for FKs, they link data but
    # don't themselves contain personal data.
    # AutoFields similarly and other auto created fields
    if isinstance(field, (models.AutoField, models.ForeignKey, GenericForeignKey)):
        return False
    if field.auto_created:
        return False
    if field.name == "erased_on" and isinstance(field, models.DateTimeField):
        return False
    return True


forever = parsy.string("forever").result(Forever)
years = (parsy.regex(r"\d+").map(int) << parsy.regex(" years?")).map(lambda y: timedelta(days=365 * y))
days = (parsy.regex(r"\d+").map(int) << parsy.regex(" days?")).map(lambda d: timedelta(days=d))
keep_parser = forever | years | days


def parse_keep(keep_value: str) -> Keep:
    try:
        return keep_parser.parse(keep_value)
    except parsy.ParseError:
        raise ValueError(f'Invalid value {keep_value} for "keep" field.')


# --- Applying ---


def apply_data_retention(policy=None, ignore_missing_models=False):
    if policy is None:
        policy = load_data_retention_policy()
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
    if rules.keep is Forever:
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
                method = _find_erasure_method(field)
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


def _find_erasure_method(field):
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
