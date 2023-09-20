"""
Parse and load data retention policy
"""
from collections.abc import Mapping
from datetime import timedelta

import parsy
import yaml
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.db.models.fields import Field

from .datatypes import ErasureMethod, Forever, Group, Keep, ModelDetail, Policy, Rules

# Basic parsers:

forever = parsy.string("forever").result(Forever)
years = (parsy.regex(r"\d+").map(int) << parsy.regex(" years?")).map(lambda y: timedelta(days=365 * y))
days = (parsy.regex(r"\d+").map(int) << parsy.regex(" days?")).map(lambda d: timedelta(days=d))
keep_parser = forever | years | days


def parse_keep(keep_value: str) -> Keep:
    try:
        return keep_parser.parse(keep_value)
    except parsy.ParseError:
        raise ValueError(f'Invalid value {keep_value} for "keep" field.')


# Parse and load whole policy


def load_data_retention_policy(available_erasure_methods: Mapping[str, ErasureMethod]) -> Policy:
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
                model_detail = build_ModelDetail(
                    name=yaml_model_name,
                    all_fields=True,
                    erasure_method_names=yaml_deletion_methods,
                    available_erasure_methods=available_erasure_methods,
                )
            else:
                yaml_delete_row = yaml_table.pop("delete row", False)
                if yaml_delete_row:
                    if yaml_columns is not None:
                        raise ValueError('You should specify either "columns" or "delete row: yes", not both')
                model_detail = build_ModelDetail(
                    name=yaml_model_name,
                    field_names=yaml_columns,
                    erasure_method_names=yaml_deletion_methods,
                    delete_row=yaml_delete_row,
                    available_erasure_methods=available_erasure_methods,
                )
            models.append(model_detail)
            if yaml_table:
                raise ValueError(f'Unexpected keys in "tables" entry: {", ".join(yaml_table.keys())}')

        try:
            group_name = yaml_group.pop("group")
        except KeyError:
            raise ValueError('Every group should have a name defined in "group" key')
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


def build_ModelDetail(
    *,
    name: str,
    field_names: list[str] | None = None,
    all_fields: bool = False,
    erasure_method_names: dict[str, str] | None = None,
    delete_row: bool = False,
    available_erasure_methods: Mapping[str, ErasureMethod],
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
        fields = [f for f in field_list if field_requires_privacy_policy(f)]

    if erasure_method_names is None:
        erasure_method_names = {}
    if all_fields:
        assert field_names is None
        fields = [f for f in field_list if field_requires_privacy_policy(f)]
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
            erasure_method = available_erasure_methods[method_name]
        except KeyError:
            raise ValueError(f'Erasure method "{method_name}" not found')
        if not erasure_method.allowed_for_field(field):
            raise ValueError(f'Erasure method "{method_name}" not allowed for {model.__name__}.{field_name}')
        erasure_methods[field] = erasure_method
    return ModelDetail(
        model=model,
        fields=fields,
        custom_erasure_methods=erasure_methods,
        delete_row=delete_row,
    )


def field_requires_privacy_policy(field: Field) -> bool:
    # By default we don't need a policy for FKs, they link data but
    # don't themselves contain personal data.
    # AutoFields similarly and other auto created fields
    if isinstance(field, models.AutoField | models.ForeignKey | GenericForeignKey):
        return False
    if field.auto_created:
        return False
    if field.name == "erased_on" and isinstance(field, models.DateTimeField):
        return False
    return True
