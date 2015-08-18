import zc.lockfile

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--debug",
                            action="store_true",
                            dest="debug",
                            default=False)

    def handle(self, *args, **options):
        try:
            l = zc.lockfile.LockFile('.handle_mail_lock')
        except zc.lockfile.LockError:
            from cciw.cciwmain.common import exception_notify_admins
            exception_notify_admins('Sending mail lock error')
            return

        try:
            try:
                from cciw.mail.lists import handle_all_mail
                handle_all_mail(debug=options['debug'])
            except:
                from cciw.cciwmain.common import exception_notify_admins
                exception_notify_admins('Sending mail error')

        finally:
            # Delete the lock
            l.close()
