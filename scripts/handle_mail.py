#!/usr/bin/env python2.4
import _cciw_env

def main():
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
            
if __name__ == '__main__':
    main()
