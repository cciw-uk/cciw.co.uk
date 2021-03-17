from django.core.management.base import BaseCommand

from cciw.mail.lists import handle_mail_from_s3


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('message_id', type=str)

    def handle(self, message_id, **options):
        handle_mail_from_s3(message_id)
