from django.conf import settings
from django.core.signals import request_started
from django.db.models.signals import post_save

from cciw.cciwmain.models import Camp, CampName, generate_colors_scss

generate_colors_scss_w = lambda sender, **kwargs: generate_colors_scss(update_existing=True)
post_save.connect(generate_colors_scss_w, CampName)


_FIRST_REQUEST_HANDLED = False


def server_startup(sender, **kwargs):
    global _FIRST_REQUEST_HANDLED
    if _FIRST_REQUEST_HANDLED:
        return
    # We do this just before the first request, at which point the
    # DB should have been initialised etc.

    if not settings.TESTS_RUNNING:
        # Make sure that the file exists, or we will get errors
        # when attempting to access the site
        generate_colors_scss(update_existing=False)

    _FIRST_REQUEST_HANDLED = True
    request_started.disconnect(server_startup)


request_started.connect(server_startup)


def recreate_ses_routes_for_camp_creation(sender, created=None, **kwargs):
    if not settings.RECREATE_ROUTES_AUTOMATICALLY:
        return
    if created:
        from cciw.mail.setup import setup_ses_routes

        setup_ses_routes()


post_save.connect(recreate_ses_routes_for_camp_creation, sender=Camp)
