from django.core.management.base import BaseCommand

from cciw.mail.lists import handle_mail


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('message_file', type=str)

    def handle(self, message_file, **options):
        with open(message_file, "rb") as f:
            data = f.read()
        handle_mail(data)
