# Utilities for creation of officers in the database# Utilities for creation of
# officers in the database
#
# Some of these are used from a script, and so print messages to the console if
# 'verbose=True'.  A bit icky...

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

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
    Create an officer with the specified username, first_name, last_name, email.
    Officer will be emailed with password.  Set username to None for an
    automatically assigned one.  Returns the created User object.
    """
    username = make_username(first_name, last_name)
    password = User.objects.make_random_password()
    officer = _create_officer(username, first_name, last_name, email, password)
    email_officer(username, first_name, email, password, update=False)
    return officer


def _create_officer(username, first_name, last_name, email, password):
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
    officer.set_password(password)
    officer.save()

    return officer


def email_officer(username, first_name, email, password, update=False):
    subject = "[CCIW] Application form system"
    msg = render_to_string('cciw/officers/add_officer_email.txt',
                           {'username': username,
                            'password': password,
                            'first_name': first_name,
                            'webmasteremail': settings.WEBMASTER_EMAIL,
                            'domain': common.get_current_domain(),
                            'update': update})

    send_mail(subject, msg, settings.WEBMASTER_EMAIL, [email])
