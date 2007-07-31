# Hooks for various events

from cciw.officers import signals
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename
from django.dispatch import dispatcher
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from django.conf import settings
import cciw.middleware.threadlocals as threadlocals

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
            email = formatted_email(leader.user)
            if email is not None:
                leader_emails.append(email)

    application_text = application_to_text(application)
    application_rtf = application_to_rtf(application)
    rtf_attachment = (application_rtf_filename(application), application_rtf, 'text/rtf')
    
    if len(leader_emails) > 0:
        send_leader_email(leader_emails, application, application_text, rtf_attachment)

    # If an admin user corrected an application, we don't send the user a copy
    # (usually they just get the year of the camp wrong(!))
    user = threadlocals.get_current_user()
    if user == application.officer:
        send_officer_email(application.officer, application, application_text, rtf_attachment)

def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "CCIW application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
"""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this email as an RTF file.

""" % application.officer.first_name) + application_text

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])



def send_leader_email(leader_emails, application, application_text, rtf_attachment):
    subject = "CCIW application form from %s" % application.full_name
    body = \
"""The following application form has been submitted via the
CCIW website.  It is also attached to this email as an RTF file.

""" + application_text
        
    send_mail_with_attachments(subject, body, settings.SERVER_EMAIL,
                               leader_emails, attachments=[rtf_attachment])


dispatcher.connect(send_application_emails, signal=signals.application_saved)
