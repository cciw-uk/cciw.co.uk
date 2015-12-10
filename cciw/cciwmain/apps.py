from django.apps import AppConfig


class CciwmainConfig(AppConfig):
    name = "cciw.cciwmain"
    verbose_name = "Camps"

    def ready(self):
        # Setup signals
        import cciw.cciwmain.hooks  # NOQA

        from cciw.cciwmain.models import generate_colors_less
        generate_colors_less()
