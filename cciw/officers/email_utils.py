from django.core.mail import EmailMessage, SMTPConnection
from django.conf import settings

"""
Utilities for sending email with attachments
"""

def send_mail_with_attachments(subject, message, from_email,
                               recipient_list, fail_silently=False,
                               auth_user=None, auth_password=None,
                               attachments=None):
    connection = SMTPConnection(username=auth_user, password=auth_password,
                                 fail_silently=fail_silently)
    return EmailMessage(subject=subject, body=message, from_email=from_email,
                        to=recipient_list, connection=connection, attachments=attachments).send()

def formatted_email(user):
    """
    Get the email address plus name of the user, formatted for
    use in sending an email, or 'None' if no email address available
    """
    name = (u"%s %s" % (user.first_name, user.last_name)).strip().replace(u'"', u'')
    email = user.email.strip()
    if len(email) == 0:
        return None
    elif len(name) > 0:
        return u'"%s" <%s>' % (name, email)
    else:
        return email
