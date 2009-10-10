# Utilities for creation of officers in the database

# Some of these are used from a script, and so print messages to the console if
# 'verbose=True'.  A bit icky...
from datetime import datetime
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.mail import send_mail
from django.forms.fields import email_re

def make_username(first_name, last_name, guess_number=1):
    """
    Makes a username for an officer, based on 'first_name' and 'last_name',
    checking in the DB for existing usernames.
    """
    first_name = first_name.lower()
    last_name = last_name.lower()
    if guess_number == 1:
        guess = "%s%s" % (first_name, last_name)
    else:
        guess = "%s%s%d" % (first_name, last_name, guess_number)
    if User.objects.filter(username=guess).count() > 0:
        return make_username(first_name, last_name, guess_number + 1)
    else:
        return guess

def create_multiple_officers(csv_data, dryrun, verbose=False):
    # csv_data is hopefully a list of lists, where each inner list
    # has 3 elements.  We have to validate it ourselves,
    # automatically generate usernames, and remember not to create
    # duplicate officers.  For this reason we use slightly different
    # logic e.g. detecting duplicates, whereas in create_single_officer
    # we trust the user.

    for officer_details in csv_data:
        valid = True

        if len(officer_details) < 3:
            valid = False
            msg = "insufficient data"

        if valid:
            first_name, last_name, email = officer_details
            first_name = first_name.strip()
            last_name = last_name.strip()
            email = email.strip()
        if valid and len(first_name) == 0:
            valid = False
            msg = "no first name provided."
        if valid and len(last_name) == 0:
            valid = False
            msg = "no surname provided"
        if valid and len(email) == 0:
            valid = False
            msg = "no email provided"
        if valid and not email_re.search(email):
            valid = False
            msg = "invalid email address"

        # We allow couples to share email addresses, so to check
        # for duplicates, we check first name as well.
        if valid and User.objects.filter(email__iexact=email, first_name__iexact=first_name).count() > 0:
            valid = False
            msg = "User with email address %s and name %s already exists" % (email, first_name)

        if valid:
            # race condition between make_username and create_single_officer,
            # but we don't care really.
            username = make_username(first_name, last_name)
            create_single_officer(username, first_name, last_name, email, dryrun=dryrun)

        else:
            if verbose:
                print "Skipping row - %s:  %r" % (msg, officer_details)

def create_officer(username, first_name, last_name, email, update=False,
                   is_leader=False, person=None, dryrun=False, verbose=False):
    """
    Create an officer with the specified username, first_name, last_name, email.
    Officer will be e-mailed with password.  Set username to None for an
    automatically assigned one.  Returns the created User object.
    """
    password = User.objects.make_random_password()
    # When called from script, the user passes in 'username', and we trust it.
    # If None is passed,
    if username is None:
        username = make_username(first_name, last_name)
    if verbose:
        if update:
            print "Updating officer %s" % username
        else:
            print "Creating officer %s" % username
    officer = _create_officer(username, first_name, last_name, email, password,
                              update=update, is_leader=is_leader, person=person,
                              dryrun=dryrun, verbose=verbose)
    if verbose:
        print "Emailing officer %s" % username
    email_officer(username, first_name, email, password, is_leader=is_leader, dryrun=dryrun, update=update)
    return officer

def _create_officer(username, first_name, last_name, email, password, dryrun=False,
                    update=False, person=None, is_leader=False, verbose=False):
    if update:
        officer = User.objects.get(username=username)
    else:
        officer = User(username=username)
        officer.date_joined=datetime.now()
        officer.last_login=datetime.now()

    officer.first_name = first_name
    officer.last_name = last_name
    officer.is_staff = True
    officer.is_active = True
    officer.is_superuser = False
    officer.email = email

    if not dryrun:
        officer.save()
        officer.set_password(password)
        officer.save()

    if is_leader:
        groupname = 'Leaders'
    else:
        groupname = 'Officers'

    if not dryrun:
        officer.groups.add(Group.objects.filter(name=groupname)[0])

        if is_leader and person is not None:
            # Make association between person and officer
            officer.person_set.add(person)
            if verbose:
                if officer.person_set.count() > 1:
                    # This can occasionally be valid e.g. if you have Person
                    # 'Joe Bloggs' and a Person 'Joe and Jane Bloggs', User
                    # joebloggs will be assoicated with both. But usually a
                    # warning will be helpful.
                    print "Warning: %r now is now associated with more than one 'Person' object." % officer
                    print "  Usually this is an error."
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


leader_template = """
Hi %(first_name)s,
%(repeat_message)s
You have been set up to receive CCIW application forms from officers
using the online system.  Here is what you need to know:

1) You will need to refer your officers to me to get login names for
   the system if they don't have them already.  If you have a list of
   officer names and email addresses, these can be imported in bulk.
   In either case, I will send them complete instructions for using
   the system.

2) After that, you will normally have nothing more to do -- you should
   receive all the application forms by email, in plain text format and
   in RTF format which should be good for printing out.

3) If you want to look at the list of people who have submitted forms,
   or if you have lost an email, you can log on to the system:

   Go to:
     https://www.cciw.co.uk/officers/

   Log in using:
     Username: %(username)s
     Password: %(password)s

     (You should change your password to something more memorable once
      you have logged in)

   At the bottom of this page you should find a link to another
   page that allows you to manage the submitted applications.


If you have any problems, please e-mail me at %(webmasteremail)s

The CCIW webmaster.
    """

def email_officer(username, first_name, email, password, is_leader=False, dryrun=False, update=False):
    if update:
        repeat_message = \
"""
This is a repeat email sent either because the first email was lost or
the password was forgotten.  Your username has not been changed, but a
new random password has been given to you, see below.
"""
    else:
        repeat_message = ""

    subject = "CCIW application form system"
    if is_leader:
        template = leader_template
    else:
        template = officer_template

    msg = template % {'username': username,
                      'password': password,
                      'first_name': first_name,
                      'webmasteremail': settings.WEBMASTER_EMAIL,
                      'repeat_message': repeat_message}

    if not dryrun:
        send_mail(subject, msg, settings.WEBMASTER_EMAIL, [email])
