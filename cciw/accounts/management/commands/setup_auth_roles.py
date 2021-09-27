from django.core.management.base import BaseCommand

from cciw.accounts.models import setup_auth_roles


class Command(BaseCommand):
    def handle(self, *args, **options):
        setup_auth_roles()
