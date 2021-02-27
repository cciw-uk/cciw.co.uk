# See config/data_retention.yaml
import dataclasses
from datetime import timedelta
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

from cciw.bookings.models import Booking


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

    @classmethod
    def build(cls, *,
              name: str,
              field_names: Optional[list[str]] = None,
              all_fields: bool = False,
              deletion_method_names: Optional[dict[str, str]] = None
              ):
        model = apps.get_model(name)
        field_list = model._meta.get_fields()
        field_dict = {f.name: f for f in field_list}
        if deletion_method_names is None:
            deletion_method_names = {}
        if all_fields:
            assert field_names is None
            fields = [f for f in field_list if _field_requires_privacy_policy(f)]
        else:
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
        return cls(model=model, fields=fields)


@dataclass
class Rules:
    keep: Optional[timedelta]
    deletable_on_request: bool


@dataclass
class Group:
    rules: Rules
    models: list[ModelDetail]


@dataclass
class Policy:
    source: str
    groups: list[Group]


class PreserveAgeOnCamp(DeletionMethod):
    def allowed_for_model(self, model):
        return model == Booking


# TODO probably want other deletion methods implemented in similar ways?
# Need to design how this will work

DELETION_METHODS = {
    'preserve_age_on_camp': PreserveAgeOnCamp(),
}


def apply_data_retention():
    policy = load_data_retention_policy()
    issues = get_data_retention_policy_issues(policy)
    if issues:
        raise AssertionError("Invalid data retention policy, aborting")
    # TODO the rest
    # We need:
    # - mechanisms for working out how to know how "old" data is for
    #   every model, and whether data is still needed for business purposes.
    #   (if we don't have it for a model, we should validate that when
    #   loading the policy).
    # - mechanisms to apply different kind of deletions, depending on field,
    #   plus custom deletion mechanisms.
    raise NotImplementedError()


def get_data_retention_policy_issues(policy: Optional[Policy] = None):
    if policy is None:
        policy = load_data_retention_policy()
    exhaustiveness_errors = _check_exhaustiveness(policy)
    return exhaustiveness_errors


def _check_exhaustiveness(policy: Policy):
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


def _field_requires_privacy_policy(field: Field):
    # By default we don't need a policy for FKs, they link data but
    # don't themselves contain personal data.
    # AutoFields similarly and other auto created fields
    if isinstance(field, (models.AutoField, models.ForeignKey, GenericForeignKey)):
        return False
    if field.auto_created:
        return False
    return True


def load_data_retention_policy() -> Policy:
    """
    Loads data_retention.yaml
    """
    # This method parses (and validates) data_retention.yaml, and also converts
    # from more "human readable" names like "tables", "columns" etc. into the
    # kind of things we actually want to use from code ("model", "fields").

    # File format/validation errors are allowed to propogate
    filename = settings.DATA_RETENTION_CONFIG_FILE
    policy_yaml = yaml.load(open(filename), Loader=yaml.SafeLoader)
    groups = []
    for yaml_group in policy_yaml:
        yaml_rules = yaml_group.pop('rules')
        keep = parse_keep(yaml_rules.pop('keep'))
        deletable_on_request = yaml_rules.pop('deletable on request from data subject')
        if yaml_rules:
            raise ValueError(f'Unexpected keys in "rules" entry: {", ".join(yaml_rules.keys())}')

        yaml_tables = yaml_group.pop('tables')
        models = []
        for yaml_table in yaml_tables:
            yaml_model_name = yaml_table.pop('name')
            yaml_columns = yaml_table.pop('columns')
            yaml_deletion_methods = yaml_table.pop('deletion methods', {})
            if yaml_columns == 'all':
                model_detail = ModelDetail.build(
                    name=yaml_model_name,
                    all_fields=True,
                    deletion_method_names=yaml_deletion_methods
                )
            else:
                model_detail = ModelDetail.build(
                    name=yaml_model_name,
                    field_names=yaml_columns,
                    deletion_method_names=yaml_deletion_methods,
                )
            models.append(model_detail)
            if yaml_table:
                raise ValueError(f'Unexpected keys in "tables" entry: {", ".join(yaml_table.keys())}')

        groups.append(
            Group(
                rules=Rules(
                    keep=keep,
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
