from django.apps import AppConfig
from django.core.checks import Tags, register


class CciwmainConfig(AppConfig):
    name = "cciw.cciwmain"
    verbose_name = "camps"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Setup signals
        import cciw.cciwmain.hooks  # NOQA


@register(Tags.models)
def check_data_retention(app_configs, **kwargs):
    from cciw.data_retention import get_data_retention_policy_issues

    return get_data_retention_policy_issues()
