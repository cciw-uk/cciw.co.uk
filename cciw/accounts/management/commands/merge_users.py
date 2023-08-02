from django.core.management.base import BaseCommand

from cciw.accounts.models import User
from cciw.accounts.utils import merge_users


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "from_username",
        )
        parser.add_argument(
            "to_username",
        )

    def handle(self, *args, **options):
        from_user = User.objects.get(username=options["from_username"])
        to_user = User.objects.get(username=options["to_username"])
        merge_users(from_user, to_user)
