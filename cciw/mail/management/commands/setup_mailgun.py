from django.core.management.base import BaseCommand

from cciw.mail.setup import setup_mailgun_routes, setup_mailgun_webhooks


class Command(BaseCommand):

    def handle(self, *args, **options):
        setup_mailgun_routes()
        setup_mailgun_webhooks()