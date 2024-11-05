from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Tags, Warning, register


class CciwmainConfig(AppConfig):
    name = "cciw.cciwmain"
    verbose_name = "camps"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Setup signals
        import cciw.cciwmain.hooks  # NOQA

        # Hacks:
        # Monkey patch pandas_highcharts to fix failure with pandas >= 2
        import pandas_highcharts.core
        import pandas

        def json_encode(obj):
            return pandas.io.json.ujson_dumps(obj)

        pandas_highcharts.core.json_encode = json_encode


@register(Tags.models)
def check_data_retention(app_configs, **kwargs):
    from cciw.data_retention.checking import get_data_retention_policy_issues

    return get_data_retention_policy_issues()


@register()
def check_date_fields(app_configs, **kwargs):
    exceptions = [
        "accounts.User.last_login",  # Provided by Django's AbstractBaseUser, we don't control
    ]
    from django.db.models import DateField, DateTimeField

    errors = []
    for field in get_first_party_fields():
        field_name = field.name
        model = field.model

        if f"{model._meta.app_label}.{model.__name__}.{field_name}" in exceptions:
            continue

        # Order of checks here is important, because DateTimeField inherits from DateField

        if isinstance(field, DateTimeField):
            if not field_name.endswith("_at"):
                errors.append(
                    Warning(
                        f"{model.__name__}.{field_name} field expected to end with `_at`, "
                        + "or be added to the exceptions in this check.",
                        obj=field,
                        id="cciw.conventions.E001",
                    )
                )
        elif isinstance(field, DateField):
            if not (field_name.endswith("_date") or field_name.endswith("_on")):
                errors.append(
                    Warning(
                        f"{model.__name__}.{field_name} field expected to end with `_date` or `_on`, "
                        + "or be added to the exceptions in this check.",
                        obj=field,
                        id="cciw.conventions.E002",
                    )
                )
    return errors


def get_first_party_fields():
    for app_config in get_first_party_apps():
        for model in app_config.get_models():
            yield from model._meta.get_fields()


def get_first_party_apps() -> list[AppConfig]:
    return [app_config for app_config in apps.get_app_configs() if is_first_party_app(app_config)]


def is_first_party_app(app_config: AppConfig) -> bool:
    if app_config.module.__name__ in settings.FIRST_PARTY_APPS:
        return True
    app_config_class = app_config.__class__
    if f"{app_config_class.__module__}.{app_config_class.__name__}" in settings.FIRST_PARTY_APPS:
        return True
    return False
