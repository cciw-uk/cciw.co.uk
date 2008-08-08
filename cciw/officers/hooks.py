# Hooks for various events

from cciw.officers import signals
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from django.conf import settings
import cciw.middleware.threadlocals as threadlocals

def send_application_emails(application):
    if not application.finished:
        return

    # Email to the leaders:
    # Collect e-mails to send to
    leaders = [user for leader in application.camp.leaders.all()
                        for user in leader.users.all()] + \
              list(application.camp.admins.all())
    leader_emails = filter(lambda x: x is not None,
                           map(formatted_email, leaders))

    application_text = application_to_text(application)
    application_rtf = application_to_rtf(application)
    rtf_attachment = (application_rtf_filename(application), application_rtf, 'text/rtf')

    if len(leader_emails) > 0:
        send_leader_email(leader_emails, application, application_text, rtf_attachment)

    # If an admin user corrected an application, we don't send the user a copy
    # (usually they just get the year of the camp wrong(!))
    user = threadlocals.get_current_user()
    if len(leader_emails) > 0:
        user.message_set.create(message="The completed application form has been sent to the leaders via email.")

    if user == application.officer:
        send_officer_email(application.officer, application, application_text, rtf_attachment)
        user.message_set.create(message="A copy of the application form has been sent to you via email.")

def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "CCIW application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
u"""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this email as an RTF file.

""" % application.officer.first_name) + application_text

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])

def send_leader_email(leader_emails, application, application_text, rtf_attachment):
    subject = "CCIW application form from %s" % application.full_name
    body = \
u"""The following application form has been submitted via the
CCIW website.  It is also attached to this email as an RTF file.

""" + application_text

    send_mail_with_attachments(subject, body, settings.SERVER_EMAIL,
                               leader_emails, attachments=[rtf_attachment])

send_application_emails_w = lambda sender, **kwargs: send_application_emails(sender)
signals.application_saved.connect(send_application_emails_w)
