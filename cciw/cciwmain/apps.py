from django.apps import AppConfig
from django.conf import settings


class CciwmainConfig(AppConfig):
    name = "cciw.cciwmain"
    verbose_name = "Camps"

    def ready(self):
        # Setup signals
        import cciw.cciwmain.hooks  # NOQA

        from cciw.cciwmain.models import generate_colors_less
        if not settings.TESTS_RUNNING:
            # Make sure that the file exists, or we will get errors
            # when attempting to access the site
            generate_colors_less(update_existing=False)
