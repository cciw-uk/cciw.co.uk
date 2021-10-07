from django.core.management.base import BaseCommand

from cciw.bookings.models import SupportingInformationDocument


class Command(BaseCommand):
    def handle(self, *args, **options):
        SupportingInformationDocument.objects.orphaned().old().delete()
