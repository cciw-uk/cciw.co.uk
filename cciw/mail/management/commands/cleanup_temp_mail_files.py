import pathlib
import tempfile
import time

from django.core.management.base import BaseCommand

from cciw.mail.lists import INCOMING_MAIL_TEMPFILE_PREFIX


class Command(BaseCommand):
    def handle(self, **options):
        start = pathlib.Path(tempfile.gettempdir())
        now = time.time()
        for path in start.glob(INCOMING_MAIL_TEMPFILE_PREFIX + '*'):
            if (now - path.stat().st_ctime) > 24 * 60 * 60:
                path.unlink()
