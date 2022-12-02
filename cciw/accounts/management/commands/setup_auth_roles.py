from django.core.management.base import BaseCommand

from cciw.accounts.models import setup_auth_roles


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="If passed, check that permissions defined in static_roles.yaml already exist in the DB",
        )

    def handle(self, *args, **options):
        setup_auth_roles(check_only=options.get("check_only", False))
