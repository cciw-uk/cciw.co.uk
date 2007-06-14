# Hooks for various events

from cciw.officers import signals
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename
from django.dispatch import dispatcher
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from django.conf import settings

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
        msg = \
"""The following application form has been submitted via the
CCIW website.  It is also attached to this email as an RTF file.

""" + application_text
    
        subject = "CCIW application form from %s" % application.full_name
    
        send_mail_with_attachments(subject, msg, settings.SERVER_EMAIL,
                                   leader_emails, attachments=[rtf_attachment])

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
"""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this email as an RTF file.

""" % application.officer.first_name) + application_text
    subject = "CCIW application form submitted"

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])


dispatcher.connect(send_application_emails, signal=signals.application_saved)
