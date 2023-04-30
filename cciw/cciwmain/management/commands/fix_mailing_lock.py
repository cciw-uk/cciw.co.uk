import os
import os.path
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Sometimes, the django-mailer 'send_mail.lock' doesn't get deleted,
        # causing mail to queue up.
        lock_file = os.path.expandvars("$HOME/send_mail.lock")
        if not os.path.exists(lock_file):
            return
        f_time = os.lstat(lock_file).st_mtime
        c_time = time.time()

        # If it's more than an hour, it's probably got stuck.
        if c_time - f_time > 60 * 60:
            os.unlink(lock_file)
