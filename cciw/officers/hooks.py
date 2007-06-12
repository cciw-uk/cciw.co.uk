# Hooks for various events

from cciw.officers import signals
from cciw.officers.applications import application_to_text
from django.dispatch import dispatcher
from django.core.mail import send_mail
from django.conf import settings
import os

def send_leader_email(application=None):
    if not application.finished:
        return
    
    leaders = application.camp.leaders.all()
    if len(leaders) == 0:
        return
    
    # Collect e-mails to send to
    emails = []
    for leader in leaders:
        # Does the leader have an associated admin login?
        if leader.user is not None:
            user = leader.user
            email = user.email.strip()
            if len(email) > 0:
                name = (user.first_name + " " + user.last_name).strip().replace('"', '')
                if len(name) > 0:
                    email = '"%s" <%s>' % (name, email)
                emails.append(email)
    if len(emails) == 0:
        return
    msg = \
"""The following application form has been submitted
via the CCIW website:

""" + application_to_text(application)
    
    subject = "CCIW application form from %s" % application.full_name
    
    send_mail(subject, msg, settings.SERVER_EMAIL, emails)

dispatcher.connect(send_leader_email, signal=signals.application_saved)
