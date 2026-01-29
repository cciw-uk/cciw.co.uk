from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django_q.tasks import async_task

from .models import Role


def recreate_ses_routes_for_role_change(sender: type[Role], created: bool | None = None, **kwargs):
    if not settings.RECREATE_ROUTES_AUTOMATICALLY:
        return
    from cciw.mail.setup import setup_ses_routes

    async_task(setup_ses_routes)


post_save.connect(recreate_ses_routes_for_role_change, sender=Role)
