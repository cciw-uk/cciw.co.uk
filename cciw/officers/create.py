# Utilities for creation of officers in the database# Utilities for creation of officers in the database

# Some of these are used from a script, and so print messages to the console if
# 'verbose=True'.  A bit icky...
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


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
    Create an officer with the specified username, first_name, last_name, e-mail.
    Officer will be e-mailed with password.  Set username to None for an
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


officer_template = """
Hi %(first_name)s,
%(repeat_message)s
An account has been set up for you on the CCIW website, which allows
you to fill in application form for coming on a CCIW camp.

Below are the instructions for filling in the application form online.
When you have finished filling the form in, it will be e-mailed to the
leader of the camp, who will need to send reference forms to the
referees you have specified.

To fill in the application form

1) Go to:
     https://www.cciw.co.uk/officers/

2) Log in using:
     Username: %(username)s
     Password: %(password)s

     (You should change your password to something more memorable once
      you have logged in)

3) Choose from the options.  If you have already completed an
   application form online, you can choose to create an application
   form based on a previous one.  Some tickboxes will be blanked out
   and you will have to fill them in again, but it should only take a
   few minutes.

   If you have not already completed an application form, you will
   have to start by creating a new one.

4) Fill in the form.

   You can save your work at any time (using the 'Save' button at the
   bottom) and come back to it later if you want.  When you have
   finished and want to submit the application form to the leaders, you
   need to check the 'Completed' checkbox at the bottom and press
   'Save'.

   Please note that if you have any validation errors (marked in red
   when you try to save), your data won't have been saved.  You'll need
   to correct the data before it is actually saved.


If you have any problems, please e-mail me at %(webmasteremail)s

The CCIW webmaster.
"""


def email_officer(username, first_name, email, password, update=False):
    if update:
        repeat_message = ("""
This is a repeat e-mail sent either because the first e-mail never
arrived or the password was forgotten.  Your username has not been
changed, but a new random password has been given to you, see below.
""")
    else:
        repeat_message = ""

    subject = "CCIW application form system"
    template = officer_template

    msg = template % {'username': username,
                      'password': password,
                      'first_name': first_name,
                      'webmasteremail': settings.WEBMASTER_EMAIL,
                      'repeat_message': repeat_message}

    send_mail(subject, msg, settings.WEBMASTER_EMAIL, [email])
