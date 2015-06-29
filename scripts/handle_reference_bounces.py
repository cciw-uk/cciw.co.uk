#!/home/cciw/webapps/cciw_django/venv_py34/bin/python
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
import django
django.setup()


def main(email_file):
    from cciw.officers.email import handle_reference_bounce
    handle_reference_bounce(email_file)

if __name__ == '__main__':
    main(sys.stdin)
