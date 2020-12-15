from django.core.management.base import BaseCommand

from cciw.mail.setup import setup_ses_routes


class Command(BaseCommand):

    def handle(self, *args, **options):
        setup_ses_routes()
