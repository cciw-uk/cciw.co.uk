#!/usr/bin/env python2.4
import sys
import os

#sys.path = sys.path + ['/home/luke/httpd/www.cciw.co.uk/django/','/home/luke/httpd/www.cciw.co.uk/django_src/', '/home/luke/httpd/www.cciw.co.uk/misc_src/']
#os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings_calvin'
sys.path = sys.path + ['/home2/cciw/webapps/django_app/', '/home2/cciw/src/django-mr/', '/home2/cciw/src/misc/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'


def usage():
    return """
Usage: create_officer.py <loginname> <firstname> <lastname> <email>
"""

def main():
    if len(sys.argv) != 5:
        print usage()
        print sys.argv
        sys.exit(1)
        
    loginname, firstname, lastname, email = sys.argv[1:]
    
    password = generate_password()
    print "Creating officer"
    create_officer(loginname, firstname, lastname, email, password)
    print "Emailing officer"
    email_officer(loginname, firstname, email, password)


def create_officer(loginname, firstname, lastname, email, password):
    from django.contrib.auth.models import User, Group
    from datetime import datetime
    
    officer = User(first_name=firstname, 
                   last_name=lastname,
                   date_joined=datetime.now(),
                   is_staff=True,
                   is_active=True,
                   is_superuser=False,
                   email=email,
                   username=loginname,
                   last_login=datetime.now())
    officer.save()
    officer.set_password(password)
    officer.save()
    officer.groups.add(Group.objects.filter(name='Officers')[0])

def email_officer(loginname, firstname, email, password):
    from django.core.mail import send_mail
    from django import template
    
    subject = "CCIW application form"
    t = template.Template("""
Hi {{ firstname }},

Below are the instructions for filling in a CCIW application form
online.  When you have finished filling the form in, it will be
e-mailed to the leader of the camp, who will need to send reference
forms to the referees you have specified.

To fill in the application form

1) Go to:
     http://www.cciw.co.uk/officers/
     
2) Log in using:
     Username: {{ loginname }}
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
    
    msg = t.render(template.Context({'loginname': loginname,
                                     'password': password,
                                     'firstname': firstname}))
    send_mail(subject, msg, "L.Plant.98@cantab.net", [email])

def generate_password():
    from random import randrange
    chars = "abcdefghijklmnopqrstuvwxyz1234567890"
    return "".join(chars[randrange(0, len(chars))] for x in range(0,8))

if __name__ == '__main__':
    main()
