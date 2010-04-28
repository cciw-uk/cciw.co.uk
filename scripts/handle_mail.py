#!/usr/bin/env python2.5
import os

def main(lockfile):
    if os.path.exists(lockfile):
        return

    try:
        # There is a race condition here, but since we only run this
        # script every n minutes, the processes are not going to be
        # racing.

        # Create the lock
        file(lockfile, "w").close()

        try:
            from cciw.mail.lists import handle_all_mail
            handle_all_mail()
        except:
            from django.core.mail import mail_admins
            import traceback
            import sys
            subject = 'Sending mail error'
            exc_info = sys.exc_info()
            message = '\n'.join(traceback.format_exception(*exc_info))
            mail_admins(subject, message, fail_silently=True)
    finally:
        # Delete the lock
        os.unlink(lockfile)

if __name__ == '__main__':
    import sys
    main(sys.argv[1])
