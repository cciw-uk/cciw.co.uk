from django.core.management.base import BaseCommand

from cciw.data_retention import apply_data_retention


class Command(BaseCommand):

    def handle(self, *args, **options):
        apply_data_retention()
