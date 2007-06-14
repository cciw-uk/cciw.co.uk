#!/usr/bin/python
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


def usage():
    return """
Usage: create_officer.py <username> <first_name> <last_name> <email>
OR:    create_officer.py --fromcsv < data.csv
OR:    create_officer.py --fromcsv --dryrun < data.csv

CSV data should be rows of <first name,last name,email>
"""

def main():
    csvmode = False
    singlemode = False
    dryrun = False
    if (len(sys.argv) == 2 or len(sys.argv) == 3) and sys.argv[1] == "--fromcsv":
        csvmode = True
        if len(sys.argv) == 3 and sys.argv[2] == '--dryrun':
          dryrun = True
    if len(sys.argv) == 5:
        singlemode = True

    if not csvmode and not singlemode:
        print usage()
        sys.exit(1)

    if singlemode:        
        username, first_name, last_name, email = sys.argv[1:]
        create_single_officer(username, first_name, last_name, email)

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
    from django.contrib.auth.models import User
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

def create_single_officer(username, first_name, last_name, email):
    password = generate_password()
    print "Creating officer %s" % username
    create_officer(username, first_name, last_name, email, password)
    print "Emailing officer %s" % username
    email_officer(username, first_name, email, password)
    
def create_officer(username, first_name, last_name, email, password):
    from django.contrib.auth.models import User, Group
    from datetime import datetime
    
    officer = User(first_name=first_name, 
                   last_name=last_name,
                   date_joined=datetime.now(),
                   is_staff=True,
                   is_active=True,
                   is_superuser=False,
                   email=email,
                   username=username,
                   last_login=datetime.now())
    officer.save()
    officer.set_password(password)
    officer.save()
    officer.groups.add(Group.objects.filter(name='Officers')[0])

def email_officer(username, first_name, email, password):
    from django.core.mail import send_mail
    from django import template
    
    subject = "CCIW application form"
    t = template.Template("""
Hi {{ first_name }},

Below are the instructions for filling in a CCIW application form
online.  When you have finished filling the form in, it will be
e-mailed to the leader of the camp, who will need to send reference
forms to the referees you have specified.

To fill in the application form

1) Go to:
     http://www.cciw.co.uk/officers/
     
2) Log in using:
     Username: {{ username }}
     Password: {{ password }}
     
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
  
  
If you have any problems, please e-mail me at L.Plant.98@cantab.net

Luke
    """)
    
    msg = t.render(template.Context({'username': username,
                                     'password': password,
                                     'first_name': first_name}))
    send_mail(subject, msg, "L.Plant.98@cantab.net", [email])

def generate_password():
    from random import randrange
    chars = "abcdefghijklmnopqrstuvwxyz1234567890"
    return "".join(chars[randrange(0, len(chars))] for x in range(0, 8))

if __name__ == '__main__':
    main()
