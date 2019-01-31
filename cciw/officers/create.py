# Utilities for creation of officers in the database# Utilities for creation of
# officers in the database
#
# Some of these are used from a script, and so print messages to the console if
# 'verbose=True'.  A bit icky...

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from cciw.cciwmain import common

User = get_user_model()


def make_username(first_name, last_name, guess_number=1):
    """
    Makes a username for an officer, based on 'first_name' and 'last_name',
    checking in the DB for existing usernames.
    """
    name = (first_name + last_name).replace(" ", "").replace("'", "").lower()
    if guess_number == 1:
        guess = name
    else:
        guess = "%s%d" % (name, guess_number)
    if User.objects.filter(username=guess).exists():
        return make_username(first_name, last_name, guess_number + 1)
    else:
        return guess


def create_officer(first_name, last_name, email):
    """
    Create an officer with the specified first_name, last_name, email.
    Officer will be emailed.  Returns the created User object.
    """
    username = make_username(first_name, last_name)
    officer = _create_officer(username, first_name, last_name, email)
    email_officer(officer, update=False)
    return officer


def _create_officer(username, first_name, last_name, email):
    officer = User(username=username)
    officer.date_joined = timezone.now()
    officer.last_login = None
    officer.first_name = first_name
    officer.last_name = last_name
    officer.is_staff = True
    officer.is_active = True
    officer.is_superuser = False
    officer.email = email
    officer.save()
    return officer


def email_officer(user, update=False, token_generator=default_token_generator):
    subject = "[CCIW] Application form system"
    msg = render_to_string('cciw/officers/add_officer_email.txt',
                           {'username': user.username,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode('ascii'),
                            'token': token_generator.make_token(user),
                            'PASSWORD_RESET_TIMEOUT_DAYS': settings.PASSWORD_RESET_TIMEOUT_DAYS,
                            'first_name': user.first_name,
                            'webmasteremail': settings.WEBMASTER_FROM_EMAIL,
                            'domain': common.get_current_domain(),
                            'update': update})

    send_mail(subject, msg, settings.WEBMASTER_FROM_EMAIL, [user.email])
