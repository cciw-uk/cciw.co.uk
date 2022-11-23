from django.apps import AppConfig
from django.core.checks import Error, Tags, register


class AccountsConfig(AppConfig):

    name = "cciw.accounts"
    default_auto_field = "django.db.models.BigAutoField"


@register(Tags.models)
def check_static_roles(app_configs, **kwargs):
    from cciw.accounts.models import setup_auth_roles

    try:
        setup_auth_roles(check_only=True)
    except Exception as e:
        return [
            Error(
                f"Error doing dry run of setup_auth_roles: {e}",
                obj=setup_auth_roles,
                id="cciw.accounts.staticroles.E001",
            )
        ]
    return []
