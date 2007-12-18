#!/usr/bin/env python2.4
import sys
import os
import socket

hostname = socket.gethostname()

if hostname == 'calvin':
    sys.path = sys.path + ['/home/luke/httpd/www.cciw.co.uk/django/','/home/luke/httpd/www.cciw.co.uk/django_src/', 
      '/home/luke/local/lib/python2.5/site-packages/', '/home/luke/devel/python/']    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings_calvin'
else:
    sys.path = sys.path + ['/home2/cciw/webapps/django_app/', '/home2/cciw/src/django-mr/', '/home2/cciw/src/misc/']
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
from django.contrib.auth.models import User


def usage():
    return \
"""Usage: create_officer.py <username> <first_name> <last_name> <email>
OR:    create_officer.py --update <username> <first_name> <last_name> <email>
OR:    create_officer.py --fromcsv < data.csv
OR:    create_officer.py --fromcsv --dryrun < data.csv

* CSV data should be rows of <first name,last name,email>
* --dryrun doesn't make any database changes
* --update mode will update the given username, resetting the password
    and re-sending the email.
"""

def main():
    csvmode = False
    singlemode = False
    dryrun = False
    if (len(sys.argv) == 2 or len(sys.argv) == 3) and sys.argv[1] == "--fromcsv":
        csvmode = True
        if len(sys.argv) == 3 and sys.argv[2] == '--dryrun':
          dryrun = True
    if (len(sys.argv) == 5 and sys.argv[1] != '--update') or (len(sys.argv) == 6 and sys.argv[1] == '--update'):
        singlemode = True

    if not csvmode and not singlemode:
        print usage()
        sys.exit(1)

    if singlemode:
        update = sys.argv[1] == '--update'
        if update:
            vars = sys.argv[2:]
        else:
            vars = sys.argv[1:]            
        username, first_name, last_name, email = vars
        create_single_officer(username, first_name, last_name, email, update=update)

    elif csvmode:
        csv_data = parse_csv_data(sys.stdin)
        create_multiple_officers(csv_data, dryrun)

def parse_csv_data(iterable):
    import csv
    return list(csv.reader(iterable))

def create_multiple_officers(csv_data, dryrun):
    # csv_data is hopefully a list of lists, where each inner list
    # has 3 elements.  We have to validate it ourselves,
    # automatically generate usernames, and remember not to create
    # duplicate officers.
    from django.core import validators
    from django.contrib.auth.models import User
    
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
        if valid and not validators.email_re.search(email):
            valid = False
            msg = "invalid email address"

        # We allow couples to share email addresses, so to check
        # for duplicates, we check first name as well.
        if valid and User.objects.filter(email__iexact=email, first_name__iexact=first_name).count() > 0:
            valid = False
            msg = "User with email address %s and name %s already exists" % (email, first_name)

        if valid:
            # race condition between get_username and create_single_officer,
            # but we don't care really.
            username = get_username(first_name, last_name)
            if dryrun:
                print "Dry run: Creating %s, %s %s %s" % (username, first_name, last_name, email)
            else:
                print "Creating %s, %s %s %s" % (username, first_name, last_name, email)
                create_single_officer(username, first_name, last_name, email)
                
        else:
            print "Skipping row - %s:  %r" % (msg, officer_details)

def get_username(first_name, last_name, guess_number=1):
    first_name = first_name.lower()
    last_name = last_name.lower()
    if guess_number == 1:
        guess = "%s%s" % (first_name, last_name)
    else:
        guess = "%s%s%d" % (first_name, last_name, guess_number)
    if User.objects.filter(username=guess).count() > 0:
        return get_username(first_name, last_name, guess_number + 1)
    else:
        return guess

def create_single_officer(username, first_name, last_name, email, update=False):
    password = User.objects.make_random_password()
    if update:
      print "Updating officer %s" % username
    else:
      print "Creating officer %s" % username
    create_officer(username, first_name, last_name, email, password, update=update)
    print "Emailing officer %s" % username
    email_officer(username, first_name, email, password)
    
def create_officer(username, first_name, last_name, email, password, update=False):
    from django.contrib.auth.models import User, Group
    from datetime import datetime

    if update:
        officer = User.objects.get(username=username)
    else:
        officer = User(username=username)
        officer.date_joined=datetime.now()
        officer.last_login=datetime.now()
        
    officer.first_name=first_name
    officer.last_name=last_name
    officer.is_staff=True               
    officer.is_active=True
    officer.is_superuser=False
    officer.email=email

    officer.validate()

    officer.save()
    officer.set_password(password)
    officer.save()
    officer.groups.add(Group.objects.filter(name='Officers')[0])

def email_officer(username, first_name, email, password):
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = "CCIW application form"
    template = """
Hi %(first_name)s,

Below are the instructions for filling in a CCIW application form
online.  When you have finished filling the form in, it will be
e-mailed to the leader of the camp, who will need to send reference
forms to the referees you have specified.

To fill in the application form

1) Go to:
     http://www.cciw.co.uk/officers/
     
2) Log in using:
     Username: %(username)s
     Password: %(password)s
     
     (You are advised to change your password to something more
      memorable once you have logged in)
      
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

Luke
    """
    
    msg = template % {'username': username,
                      'password': password,
                      'first_name': first_name,
                      'webmasteremail': settings.WEBMASTER_EMAIL}
    send_mail(subject, msg, settings.WEBMASTER_EMAIL, [email])


if __name__ == '__main__':
    main()
