"""
Checks on data retention policy (beyond basic validity checks)
"""
from django.apps import apps
from django.core.checks import Error

from .applying import ERASABLE_RECORDS, ERASED_ON_EXCEPTIONS, find_erasure_method, load_actual_data_retention_policy
from .loading import Forever, Policy, field_requires_privacy_policy


def get_data_retention_policy_issues(policy: Policy | None = None):
    if policy is None:
        policy = load_actual_data_retention_policy()
    return _check_exhaustiveness(policy) + _check_erasable_records(policy)


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
            if not field_requires_privacy_policy(field):
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
                        find_erasure_method(field)
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
