from django.core.management.base import BaseCommand

from cciw.bookings.models import expire_bookings


class Command(BaseCommand):
    def handle(self, *args, **options):
        expire_bookings()
