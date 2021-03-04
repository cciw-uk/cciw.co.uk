# See config/data_retention.yaml
import dataclasses
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

import parsy
import pydantic.dataclasses
import yaml
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.checks import Error
from django.db import models
from django.db.models.fields import Field
from django.utils import timezone

from cciw.bookings.models import Booking
from cciw.contact_us.models import Message


class DataclassConfig:
    arbitrary_types_allowed = True


dataclass = pydantic.dataclasses.dataclass(config=DataclassConfig)

if TYPE_CHECKING:
    # Help some type checkers/IDE tools to understand pydantic
    from dataclasses import dataclass


class DeletionMethod:
    def allowed_for_model(self, model):
        raise NotImplementedError()

    def apply(self, queryset):
        raise NotImplementedError()


@dataclass
class ModelDetail:
    model: type  # Model subclass
    fields: list[Field]
    deletion_methods: dict[Field, DeletionMethod] = dataclasses.field(default_factory=dict)
    delete_row: bool = False

    @classmethod
    def build(cls, *,
              name: str,
              field_names: Optional[list[str]] = None,
              all_fields: bool = False,
              deletion_method_names: Optional[dict[str, str]] = None,
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
            if deletion_method_names:
                raise ValueError("If 'delete_row' is used, no deletion methods should be specified.")
            # We satisfy exhaustiveness checks easier with this:
            fields = [f for f in field_list if _field_requires_privacy_policy(f)]

        if deletion_method_names is None:
            deletion_method_names = {}
        if all_fields:
            assert field_names is None
            fields = [f for f in field_list if _field_requires_privacy_policy(f)]
        elif not delete_row:
            assert field_names is not None
            fields = []
            for f in field_names:
                if f not in field_dict:
                    raise ValueError(f'Model {model.__name__} does not have field {f}')
                fields.append(field_dict[f])

        deletion_methods = {}
        for field_name, method_name in deletion_method_names.items():
            try:
                deletion_method = DELETION_METHODS[method_name]
            except KeyError:
                raise ValueError(f'Deletion method "{method_name}" not found')
            deletion_methods[field_dict[field_name]] = deletion_method
        return cls(
            model=model,
            fields=fields,
            deletion_methods=deletion_methods,
            delete_row=delete_row,
        )


@dataclass
class Rules:
    # We use 'keep' in YAML, with 'forever' as a special value, for human readability.
    # To avoid ambiguity with `keep == None`, we use the name `delete_after`
    # in code, so we have `delete_after == None` meaning keep forever.
    delete_after: Optional[timedelta]
    deletable_on_request: bool


@dataclass
class Group:
    rules: Rules
    models: list[ModelDetail]


@dataclass
class Policy:
    source: str
    groups: list[Group]


# --- Parsing and checking ---


def get_data_retention_policy_issues(policy: Optional[Policy] = None):
    if policy is None:
        policy = load_data_retention_policy()
    return (
        _check_exhaustiveness(policy) +
        _check_deletable_records(policy)
    )


def load_data_retention_policy() -> Policy:
    """
    Loads data_retention.yaml
    """
    # This method parses (and validates) data_retention.yaml, and also converts
    # from more "human readable" names like "tables", "columns" etc. into the
    # kind of things we actually want to use from code ("model", "fields").

    # A lot of complexity here is trying to keep the YAML human readable
    # and not redundant, and making sure we validate lots of possible errors.

    # File format/validation errors are allowed to propogate
    filename = settings.DATA_RETENTION_CONFIG_FILE
    policy_yaml = yaml.load(open(filename), Loader=yaml.SafeLoader)
    groups = []
    for yaml_group in policy_yaml:
        yaml_rules = yaml_group.pop('rules')
        delete_after = parse_keep(yaml_rules.pop('keep'))
        deletable_on_request = yaml_rules.pop('deletable on request from data subject')
        if yaml_rules:
            raise ValueError(f'Unexpected keys in "rules" entry: {", ".join(yaml_rules.keys())}')

        yaml_tables = yaml_group.pop('tables')
        models = []
        for yaml_table in yaml_tables:
            yaml_model_name = yaml_table.pop('name')
            yaml_columns = yaml_table.pop('columns', None)
            yaml_deletion_methods = yaml_table.pop('deletion methods', {})
            if yaml_columns == 'all':
                if 'delete row' in yaml_table:
                    raise ValueError('You should specify either "columns: all" or "delete row", not both')
                model_detail = ModelDetail.build(
                    name=yaml_model_name,
                    all_fields=True,
                    deletion_method_names=yaml_deletion_methods
                )
            else:
                yaml_delete_row = yaml_table.pop('delete row', False)
                if yaml_delete_row:
                    if yaml_columns is not None:
                        raise ValueError('You should specify either "columns" or "delete row: yes", not both')
                model_detail = ModelDetail.build(
                    name=yaml_model_name,
                    field_names=yaml_columns,
                    deletion_method_names=yaml_deletion_methods,
                    delete_row=yaml_delete_row,
                )
            models.append(model_detail)
            if yaml_table:
                raise ValueError(f'Unexpected keys in "tables" entry: {", ".join(yaml_table.keys())}')

        groups.append(
            Group(
                rules=Rules(
                    delete_after=delete_after,
                    deletable_on_request=deletable_on_request,
                ),
                models=models
            )
        )
        if yaml_group:
            raise ValueError(f'Unexpected keys in group entry: {", ".join(yaml_group.keys())}')

    return Policy(
        source=filename,
        groups=groups
    )


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
        issues.append(Error(
            'Duplicate policies were found for some fields:\n' +
            ''.join(f'   - {model.__name__}.{field}\n' for model, field in dupes),
            obj=policy.source,
            id='dataretention.E001'
        ))
    if missing:
        msg_parts = ['Missing models/fields:']
        for model, missing_for_model in missing:
            # Mimic the format of data_retention.yaml for easy copy/paste
            msg_parts.append(f'    - name: {model._meta.app_label}.{model.__name__}')
            msg_parts.append('      columns:')
            for field in missing_for_model:
                msg_parts.append(f'      - {field.name}')
        issues.append(Error(
            '\n'.join(msg_parts) + '\n',
            obj=policy.source,
            id='dataretention.E002',
        ))

    return issues


def _check_deletable_records(policy: Policy) -> list[Error]:
    seen_models = set()
    issues = []
    if True:
        # TODO - remove this when we are ready to deploy data retention for
        # real.
        return issues
    for group in policy.groups:
        if group.rules.delete_after is None and not group.rules.deletable_on_request:
            # Don't need deletion method
            continue

        for model_detail in group.models:
            model = model_detail.model
            if model in seen_models:
                continue
            seen_models.add(model)
            if model not in DELETABLE_RECORDS:
                issues.append(Error(
                    f'No method for defined to obtain deletable records for {model.__name__}',
                    obj=policy.source,
                    id='dataretention.E003'
                ))
    return issues


def _field_requires_privacy_policy(field: Field):
    # By default we don't need a policy for FKs, they link data but
    # don't themselves contain personal data.
    # AutoFields similarly and other auto created fields
    if isinstance(field, (models.AutoField, models.ForeignKey, GenericForeignKey)):
        return False
    if field.auto_created:
        return False
    return True


forever = parsy.string('forever').result(None)
years = (parsy.regex(r'\d+').map(int) << parsy.regex(" years?")).map(
    lambda y: timedelta(days=365 * y)
)
days = (parsy.regex(r'\d+').map(int) << parsy.regex(" days?")).map(
    lambda d: timedelta(days=d)
)
keep_parser = forever | years | days


def parse_keep(keep_value: str) -> Optional[timedelta]:
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
            issues = [issue for issue in issues if 'Missing models' not in issue.msg]
        if issues:
            raise AssertionError("Invalid data retention policy, aborting", issues)
    # TODO the rest
    # We need:
    # - mechanisms for working out how to know how "old" data is for
    #   every model, and whether data is still needed for business purposes.
    #   (if we don't have it for a model, we should validate that when
    #   loading the policy).
    # - mechanisms to apply different kind of deletions, depending on field,
    #   plus custom deletion mechanisms.

    now = timezone.now()
    retval = []
    for group in policy.groups:
        for model_detail in group.models:
            retval.append(apply_data_retention_single_model(now, rules=group.rules, model_detail=model_detail))
    return retval


def apply_data_retention_single_model(now: datetime, *, rules: Rules, model_detail: ModelDetail):
    if rules.delete_after is None:
        return []

    delete_before_date = now - rules.delete_after
    # TODO probably want separate method for manual erasure requests,
    # need to be careful about things that are still needed and
    # how to respect `delete_after`
    deletable_records = get_deletable(delete_before_date, model_detail.model)
    if model_detail.delete_row:
        retval = deletable_records.delete()
    else:
        raise NotImplementedError()
    return retval


def get_deletable(before_date, model: type):
    return DELETABLE_RECORDS[model](before_date)

# --- Model specific knowledge ---


class PreserveAgeOnCamp(DeletionMethod):
    def allowed_for_model(self, model):
        return model == Booking


DELETABLE_RECORDS = {
    Message: lambda before_date: Message.objects.filter(timestamp__lt=before_date),
}
# TODO probably want other deletion methods implemented in similar ways?
# Need to design how this will work

DELETION_METHODS = {
    'preserve_age_on_camp': PreserveAgeOnCamp(),
}
