import datetime
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Removes links created for serving secure files if they have expired'

    def handle(self, *args, **kwargs):
        now = datetime.datetime.now()
        for d in os.listdir(settings.SECUREDOWNLOAD_SERVE_ROOT):
            parts = d.split('-')
            if len(parts) != 2:
                continue
            try:
                ts = int(parts[0])
            except ValueError:
                continue
            dt = datetime.datetime.fromtimestamp(ts)
            td = now - dt
            if (td.days * 3600 * 24) + td.seconds < settings.SECUREDOWNLOAD_TIMEOUT:
                continue

            # Delete the directory and all contents.
            shutil.rmtree(os.path.join(settings.SECUREDOWNLOAD_SERVE_ROOT, d))
