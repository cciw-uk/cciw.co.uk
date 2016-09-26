from django.core.management.base import BaseCommand

from cciw.mail.setup import setup_mailgun_routes


class Command(BaseCommand):

    def handle(self, *args, **options):
        setup_mailgun_routes()
