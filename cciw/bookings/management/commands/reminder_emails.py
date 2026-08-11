from django.core.management.base import BaseCommand

from cciw.bookings.email import send_payment_reminder_emails


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_payment_reminder_emails()
