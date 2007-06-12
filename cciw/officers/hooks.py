# Hooks for various events

from cciw.officers import signals
from cciw.officers.applications import application_to_text
from django.dispatch import dispatcher
from django.core.mail import send_mail
from django.conf import settings
import os

def _formatted_email(user):
    """
    Get the email address plus name of the user, formatted for
    use in sending an email, or 'None' if no email address available
    """
    name = (user.first_name + " " + user.last_name).strip().replace('"', '')
    email = user.email.strip()
    if len(email) == 0:
        return None
    elif len(name) > 0:
        return '"%s" <%s>' % (name, email)
    else:
        return email

def send_application_emails(application=None):
    if not application.finished:
        return

    # Email to the leaders:
    leaders = application.camp.leaders.all()
    
    # Collect e-mails to send to
    leader_emails = []
    for leader in leaders:
        # Does the leader have an associated admin login?
        if leader.user is not None:
            email = _formatted_email(leader.user)
            if email is not None:
                leader_emails.append(email)

    application_text = application_to_text(application)
    if len(leader_emails) > 0:
        msg = \
"""The following application form has been submitted
via the CCIW website:

""" + application_text
    
        subject = "CCIW application form from %s" % application.full_name
    
        send_mail(subject, msg, settings.SERVER_EMAIL, leader_emails)

    # Email to the officer
    user_email = _formatted_email(application.officer)
    user_msg = (
"""%s,

For your records, here is a copy of the application you have submitted
to CCIW.

""" % application.officer.first_name) + application_text
    subject = "CCIW application form submitted"

    if user_email is not None:
        send_mail(subject, user_msg, settings.SERVER_EMAIL, [user_email])

dispatcher.connect(send_application_emails, signal=signals.application_saved)
