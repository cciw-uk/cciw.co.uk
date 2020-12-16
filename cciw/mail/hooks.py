from django.conf import settings
from django.db.models.signals import post_save

from .models import EmailForward


def recreate_ses_routes_for_email_forward_change(sender, created=None, **kwargs):
    if not settings.RECREATE_ROUTES_AUTOMATICALLY:
        return
    from cciw.mail.setup import setup_ses_routes
    setup_ses_routes()


post_save.connect(recreate_ses_routes_for_email_forward_change, sender=EmailForward)
